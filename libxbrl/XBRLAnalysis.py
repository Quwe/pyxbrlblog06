from bs4 import BeautifulSoup
from .XMLDataGetter import XMLDataGetter
import os
import pickle
import hashlib

class XBRLAnalysisError(Exception):
	pass

#XBRLドキュメントのツリー構造
class XBRLStructureTree():

	def __init__(self, file_path):


		self.__init_xbrl_file_path(file_path)


		#データの読み込みに成功しようがどうだろうがルートだけは用意しておく
		self.root_node = XBRLStructureNode('document_root', 'root')
		self.root_node.set_href('root')


		#木構造巡回のための復帰情報を詰んでおくためのスタック
		#通常はルートから巡回を開始する
		self.init_walking_status() 


		#表示リンクベースファイルの解析を始める
		soup = XMLDataGetter.get(file_path)


		#親子関係読み込み後のhref取得に用いる
		roleRef_elems = soup.select('roleRef')
		loc_elems = soup.select('loc')	


		#roleRef要素の一覧を保存
		self.__rol_list = list()
		for elem in roleRef_elems :
			self.__rol_list.append( elem.get('xlink:href').split('#')[-1] )



		#まずはリンク構造(親子関係)を読み込み木構造を生成する


		#presentationLinkごとに構造を取得する
		document_number = 0
		for primary_item in soup.select('presentationLink'):

			document_number = document_number + 1

			#大項目の名称を取得
			primary_item_name = primary_item.get('xlink:role')
			sub_root_node = XBRLStructureNode(primary_item_name, 'document_name')

			#大項目のhref属性を設定
			for elem in roleRef_elems :
				if elem.get('roleURI') == sub_root_node.label_in_pre_linkbase :
					sub_root_node.set_href(elem.get('xlink:href') )
					break


			self.root_node.append_child(sub_root_node, document_number)


			#各要素を保存するための辞書
			tree_dict = {}


			#presentationLink内の各要素の親子関係を取得し保存する
			for elem in primary_item.select('presentationArc'):

				parent_name = elem.get('xlink:from')
				child_name = elem.get('xlink:to')
				order_str = elem.get('order')
				preferred_label = elem.get('preferredLabel')

				order = None
				if order_str != None :
					order = float(order_str)

				parent = None
				child = None


				if parent_name not in tree_dict:
					parent = XBRLStructureNode(parent_name, 'content')
					tree_dict[parent_name] = parent
				else :
					parent = tree_dict[parent_name]


				if child_name not in tree_dict:
					child = XBRLStructureNode(child_name, 'content')
					tree_dict[child_name] = child
				else :
					child = tree_dict[child_name]


				parent.append_child(child, order)
				child.parent = parent


				if preferred_label != None :
					child.preferred_label = preferred_label



			#親子関係を読み込めたら、各項目のhref属性を設定する
			for key in tree_dict.keys():

				node = tree_dict[key]

				for elem in loc_elems :
					if elem.get('xlink:label') == node.label_in_pre_linkbase :

						#loc要素の中にはhref要素のURIがローカルファイルのケースが存在する
						#(提出者の独自要素の場合)
						#この場合はhrefの値を参照可能なパスに修正する
						tmp_href = elem.get('xlink:href')
						if not tmp_href.startswith('http') :
							tmp_href = os.path.join(self.get_xbrl_dir_path(), tmp_href)


						node.set_href(tmp_href)
						break




			#保存結果には親が設定されていないノードが存在するため、ここで設定する
			no_parent_node_list = list()
			for key in tree_dict.keys():
				current_node = tree_dict[key]

				if current_node.parent == None :
					no_parent_node_list.append(current_node)


			#idが*Heading*となるノードが最上位ノードなのでこれをまず探す
			#ただし、これは命名規則によるものなので副作用があるかもしれない
			#親無しノードのidとしてHeadingが使われていないという前提の処理
			#もしこれがダメならスキマーファイルを調べて、更に絞り込む必要がある
			heading_node = None
			for no_parent_node in no_parent_node_list :
				if 'Heading' in no_parent_node.id :
					heading_node = no_parent_node
					break


			#EDINET XBRLのガイドラインを見る限り
			#Headingノードは必ず存在するはず
			if heading_node == None :
				raise Exception('no heading node error')


			sub_root_node.append_child(heading_node, 1.0)
			no_parent_node_list.remove(heading_node)


			#Headingノード以外の親無しを処理する
			while len(no_parent_node_list) > 0 :

				#Headingから辿って、子に親無しを持つノードを探す

				#(node, child_index)
				result_tuple = (None, -1)
				source_node = None
				for no_parent_node in no_parent_node_list :

					result_tuple = XBRLStructureTree.__search_node_that_have_target_id_child(heading_node, no_parent_node.id)
					if result_tuple[0] != None :
						source_node = no_parent_node
						break

				#親無しはHeading以下に必ず存在する
				if result_tuple[0] == None :
					raise Exception('no parent node is not exists in heading node')


				node_that_have_target_label_child = result_tuple[0]
				child_index = result_tuple[1]


				#優先ラベルと順序は親無しには絶対設定されていない
				#したがって、挿入先のものを使用する
				source_node.order = node_that_have_target_label_child.children[child_index].order
				source_node.preferred_label = node_that_have_target_label_child.children[child_index].preferred_label

				#親無しを挿入する
				node_that_have_target_label_child.children[child_index] = source_node

				no_parent_node_list.remove(source_node)


		#優先ラベルを設定する
		self.__set_preferred_label(self.root_node, None)


	@staticmethod
	def __search_node_that_have_target_id_child(node, id) :

		result_node = None
		result_index = -1

		#まず自分自身を調べる
		for index, child in enumerate(node.children) :

			if child.id == id :

				result_node = node
				result_index = index
				break


		#発見したら結果を返す
		if result_node != None :
			return result_node, result_index


		#次に子供を調べる
		for child in node.children :

			result_tuple = XBRLStructureTree.__search_node_that_have_target_id_child(child, id)
			if result_tuple[0] != None :

				return result_tuple[0], result_tuple[1]


		#発見できず
		return None, -1


	#優先ラベル情報を設定する
	def __set_preferred_label(self, target_node, parent_preferred_label):

		#親の優先ラベルが設定されており、設定対象の優先ラベルが設定されていない場合のみ
		#設定対象のノードの優先ラベルを設定する

		if target_node.preferred_label == None and parent_preferred_label != None :

			target_node.preferred_label = parent_preferred_label


		for child in target_node.children :
			self.__set_preferred_label(child, target_node.preferred_label)


	#名称リンクベースファイル(日本語)を読み込み、各ノードの日本語名称を取得する
	def read_jp_lab_file(self, rol_id) :

		#存在しないrolを指定された場合は処理しない
		if rol_id not in self.__rol_list :
			return


		#木構造巡回のルートを設定する
		self.set_walking_root(self.__search_node(rol_id))



		#本XBRLが参照する名称リンクベースファイル(日本語)の一覧を取得する
		soup = XMLDataGetter.get(self.get_xsd_file_path())

		labfile_list = list()

		for elm in  soup.select('linkbaseRef') :

			tmp_href = elm.get('xlink:href')
			if tmp_href.startswith('http') and tmp_href.endswith('_lab.xml') :
				labfile_list.append(tmp_href)

		if os.path.exists(self.get_lab_file_path()) :
			labfile_list.append(self.get_lab_file_path())



		#名称リンクベースファイル（日本語)を読み込む
		labfile_structure_dicts = {}

		for labfile in labfile_list :

			jp_str_label_records = list()

			#まずローカルに名称リンクベースを読み込んだデータがないか確認する
			#存在するなら過去の読み込み結果を使う

			hash_str = hashlib.sha256(labfile.encode('utf-8')).hexdigest()
			bin_file_name = '.' + os.sep + 'labfile' + os.sep + 'labfile_structure_' + labfile.translate(str.maketrans('/\\.:', '____')) +'_' + hash_str

			if os.path.isfile(bin_file_name) :

				with open(bin_file_name, 'rb') as f:

					jp_str_label_records = pickle.load(f)
					labfile_structure_dicts[labfile] = jp_str_label_records

				continue


			#ファイルが存在しないなら一から読み込み処理を実行する
			jp_str_label_records = list()

			soup = XMLDataGetter.get(labfile)

			loc_elms= soup.select('loc')
			label_arc_elms = soup.select('labelArc')
			label_elms =  soup.select('label')


			for loc_elm in loc_elms :


				#loc要素から要素IDに対応するラベルを辿るためのリンク名称を取得する
				elm_href =  loc_elm.get('xlink:href')
				elm_id = elm_href.split('#')[-1]

				link_name = loc_elm.get('xlink:label')


				#リンク名からIDにリンクされているラベルを取得する
				for label_arc_elm in label_arc_elms :

					if not label_arc_elm.get('xlink:from') == link_name :

						continue


					label_id = label_arc_elm.get('xlink:to')

					for label_elm in label_elms :


						if not label_elm.get('xlink:label') == label_id :

							continue

						jp_label = str(label_elm.string)
						label_role = label_elm.get('xlink:role')


						jp_str_label_records.append(JPStrLabelRecord(elm_id, label_role, jp_label))




			labfile_structure_dicts[labfile] = jp_str_label_records


			with open(bin_file_name, 'wb') as f:

				 pickle.dump(jp_str_label_records, f)




		#各ノードの日本語名称を設定する
		for node in self :

			#role要素は処理しない
			if node.node_kind == 'document_name' :
				continue



			#要素のスキーマファイルのURIから参照するべき名称リンクベースを取得する
			targeted_labfile = None

			schema_url = node.get_href().split('#')[0]

			if schema_url.startswith('http') :
				sep = '/'
			else :
				sep = os.sep

			schema_dir = sep.join(schema_url.split(sep)[0:-1])

			for labfile in labfile_list :

				if labfile.startswith(schema_dir) :
					targeted_labfile = labfile
					break

			if targeted_labfile == None :
				raise XBRLAnalysisError('ノードに対応する名称リンクベースファイルを発見できませんでした')


			#名称リンクベースファイルに対応するレコードリストを取得する
			label_records = labfile_structure_dicts[targeted_labfile]


			#レコードリストを検索する
			schema_id = node.get_id()
			jp_str = None

			for record in label_records :

				if schema_id == record.id and record.role == node.preferred_label :

					jp_str = record.jp_str
					break


			#デフォルトは標準ラベルを用いる
			if jp_str == None :
				for record in label_records :
					if schema_id == record.id and record.role == 'http://www.xbrl.org/2003/role/label' :

						jp_str = record.jp_str
						break


			node.set_jp_label(jp_str)


	#xsdファイルの読み込み
	def read_xsd_file(self, rol_id) :

		#存在しないrolを指定された場合は処理しない
		if rol_id not in self.__rol_list :
			return


		#木構造巡回のルートを設定する
		self.set_walking_root(self.__search_node(rol_id))


		#xsdファイルを検索し、各ノードの詳細情報から用途を調べる
		for node in self :

			#role要素は処理しない
			if node.node_kind == 'document_name' :
				continue

			soup = XMLDataGetter.get(node.get_xsd_uri() )
			if soup == None :

				raise XBRLAnalysisError('スキーマファイルが存在しない:' + node.get_xsd_uri())


			detail_elm = soup.select_one('#' + node.get_id() )
			if detail_elm == None :

				raise XBRLAnalysisError('スキーマファイルに該当要素無し:' + node.get_href())


			#必要な属性を取得
			tmp_name = detail_elm.get('name').split(':')[-1]
			tmp_type = detail_elm.get('type').split(':')[-1]
			tmp_substitutionGroup = detail_elm.get('substitutionGroup').split(':')[-1]


			#abstractが設定されていない場合はfalseと判断
			#暫定
			if detail_elm.get('abstract') == None :
				tmp_abstract = 'false'
			else :
				tmp_abstract = detail_elm.get('abstract').split(':')[-1]


			#属性の値から用途を判別
			if 'Heading' in tmp_name and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'identifierItem' and tmp_abstract == 'true' :
				node.set_usage('heading')

			elif 'Abstract' in tmp_name  and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'item' and tmp_abstract == 'true' :
				node.set_usage('title')

			elif 'Table' in tmp_name and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'hypercubeItem' and tmp_abstract == 'true' :
				node.set_usage('table')

			elif 'Axis' in tmp_name and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'dimensionItem' and tmp_abstract == 'true' :
				node.set_usage('axis')

			elif 'Member' in tmp_name and tmp_type == 'domainItemType' and tmp_substitutionGroup == 'item' and tmp_abstract == 'true' :
				node.set_usage('member')

			elif 'LineItems' in tmp_name and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'item' and tmp_abstract == 'true' :
				node.set_usage('line_items')

			elif tmp_abstract == 'false' and ( tmp_type == 'monetaryItemType' or \
								tmp_type == 'perShareItemType' or \
								tmp_type == 'sharesItemType' or \
								tmp_type == 'percentItemType' or \
								tmp_type == 'decimalItemType' or \
								tmp_type == 'nonNegativeIntegerItemType') :
				node.set_usage('number')

			elif tmp_abstract == 'false' and ( tmp_type == 'dateItemType') :
				node.set_usage('date')

			elif 'TextBlock' in tmp_name and tmp_abstract == 'false' and ( tmp_type == 'textBlockItemType' ) :

				node.set_usage('text_block')

			elif tmp_abstract == 'false' and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'item' :

				node.set_usage('text')

			elif tmp_type == 'stringItemType' and tmp_substitutionGroup == 'item' and tmp_abstract == 'true' :
				node.set_usage('title')

			else :
				raise XBRLAnalysisError('要素用途の判定結果例外:'+detail_elm.prettify())


			node.set_name(tmp_name)


	def show_tree(self, show_node_id = 'root') :

		#rootおよびrol_list中のノードのみ受け付ける
		if show_node_id != 'root' and show_node_id not in self.__rol_list :

			print('不正なノード指定:' + show_node_id)
			return


		#表示ルートノードの設定
		show_node = self.__search_node(show_node_id)

		#木構造の表示処理
		self.__print_all_node(show_node, 0)


	#指定されたノードに連なるノードを全て表示する
	def __print_all_node(self, root_node, depth):

		order = 'None'	
		if root_node.order != None :
			order = root_node.order	

		#print('     '*depth,str(root_node.href).split('#')[-1], '  ', order, ' th : label ', root_node.preferred_label)
		print('     '*depth + '(' + str(root_node.get_usage()) + ')' + root_node.get_id() + '(' + str(root_node.get_jp_label()) + ')' + '  : ' +  str(root_node.preferred_label) )

		root_node.children.sort()
		for child in root_node.children :
			self.__print_all_node(child, depth + 1)


	#ロールリストを取得する
	def get_rol_list(self) :
		return self.__rol_list


	#ノードを検索する
	def __search_node(self, id) :

		result = None

		for elm in self :

			if str(elm.href).split('#')[-1] == id :
				result = elm



		return result


	#読み込むXBRLファイルのパスを保存
	def __init_xbrl_file_path(self, pre_linkbase_file_path) :

		local_xbrl_dir_path = os.path.dirname(pre_linkbase_file_path)
		local_xbrl_basename = os.path.basename(pre_linkbase_file_path).replace('_pre.xml','')


		local_xsd_name = local_xbrl_basename + '.xsd'
		local_lab_name = local_xbrl_basename + '_lab.xml'
		local_def_name = local_xbrl_basename + '_def.xml'
		local_xbrl_name = local_xbrl_basename + '.xbrl'

		self.__xsd_file_path = os.path.join(local_xbrl_dir_path, local_xsd_name)
		self.__lab_file_path = os.path.join(local_xbrl_dir_path, local_lab_name)
		self.__xbrl_file_path = os.path.join(local_xbrl_dir_path, local_xbrl_name)
		self.__def_linkbase_file_path = os.path.join(local_xbrl_dir_path, local_def_name)
		self.__pre_linkbase_file_path = pre_linkbase_file_path

		self.__xbrl_dir_path = local_xbrl_dir_path


	def get_xbrl_dir_path(self):
		return self.__xbrl_dir_path

	def get_xsd_file_path(self) :
		return self.__xsd_file_path

	def get_lab_file_path(self) :
		return self.__lab_file_path



	#イテレーターを実装


	#巡回情報スタックへのアクセスは全てこれらの関数郡で行う
	#完全な隠蔽は無理だけど少しはましなはず

	def get_top_walk_info(self):

		if len(self.walk_info_stack) == 0 :
			return None


		else :
			return self.walk_info_stack[-1]

	def pop_walk_info(self) :
		if len(self.walk_info_stack) == 0 :
			return None

		else :
			return self.walk_info_stack.pop()


	def append_walk_info(self, walk_info) :
		self.walk_info_stack.append(walk_info)



	#巡回状況を初期化する
	#デフォルトはルート
	def init_walking_status(self) :
		self.walk_info_stack = list()
		self.walk_info_stack.append(WalkInfo(self.root_node))


	#与えられたノードをルートとして巡回する
	def set_walking_root(self, node) :
		self.walk_info_stack = list()
		self.walk_info_stack.append(WalkInfo(node))



	#イテレータのインターフェース関数
	def __iter__(self):

		return self

	#イテレータのインターフェース関数
	def __next__(self):

		return self.walk_next_node()


	#次の要素に巡回する
	#
	#巡回情報スタックに応じて動作する
	#
	#スタックの最上位の要素を巡回していく
	#子要素がある時はスタックし、親要素に戻るときはポップする
	#スタックが空になった時が巡回を終了するべき時である
	#
	#スタックの一番底が巡回対象となる木構造のルートとなっている
	#部分木のみ巡回したければ、このスタックの一番底を部分木のルートにしておけばよい
	#
	#
	#巡回先の決定アルゴリズム
	#
	#1.巡回情報スタックが空なら巡回を終える
	#  巡回を終える際はスタックに次に巡回する木構造の
	#  最上位ノード情報のみがある状態にしておく
	#
	#2.スタックの最上位が未巡回ならそこを巡回する
	#
	#3.スタックの最上位の子要素を巡回する
	#  子要素を巡回する際はスタックに子要素ノードの情報を積み
	#　再度1から処理を継続する
	#
	#4.子要素を巡回しきったら、親要素を巡回する
	#  親要素を巡回する際はスタックをポップし
	#　再度1から処理を継続する
	#
	def walk_next_node(self):

		#巡回情報が空なら巡回は完了している	
		top_walk_info = self.get_top_walk_info()
		if top_walk_info == None :
			self.end_walking()


		#自身を巡回してないなら自身を巡回する
		if top_walk_info.current_node_returned == False :
			top_walk_info.current_node_returned = True
			return top_walk_info.current_node	


		#いまのノードにとって子ノードの巡回がはじめてなら
		#子ノードの巡回情報の初期化が必要
		if top_walk_info.last_returned_child_index == -1 and len(top_walk_info.current_node.children) != 0 :
			top_walk_info.number_of_children =  len(top_walk_info.current_node.children)

			#初回だけ子ノードのソートを実施する
			top_walk_info.current_node.children.sort()


		#いま巡回する子ノードのインデックスは前回巡回した子ノードのインデックスの次である
		child_index = top_walk_info.last_returned_child_index + 1


		#最後の子ノードを巡回済みであれば親の巡回を再開する
		if top_walk_info.number_of_children <=  child_index :
			self.pop_walk_info()
			return self.walk_next_node()	


		#子ノードを巡回する
		top_walk_info.last_returned_child_index = top_walk_info.last_returned_child_index + 1
		self.append_walk_info(WalkInfo(top_walk_info.current_node.children[child_index]))	
		return self.walk_next_node()


		#ここに到達することはあり得ない


	#巡回を終了する
	def end_walking(self) :
		self.init_walking_status()
		raise StopIteration()


#巡回情報
class WalkInfo():

	def __init__(self, current_node):
		self.current_node = current_node

		#自身を巡回済みか否か
		self.current_node_returned = False

		#子ノードの巡回状況を保持
		self.last_returned_child_index = -1 
		self.number_of_children = 0


#ノード
class XBRLStructureNode():


	def __init__(self, label_in_pre_linkbase, node_kind):


		#ノードの種別
		# 'root'          読み込みのために存在
		# 'document_name' 有報表示構造における大項目
		# 'content'       大項目の下にある構造要素
		self.node_kind = node_kind


		#表示リンクベースファイル中のラベル属性
		self.label_in_pre_linkbase = label_in_pre_linkbase

		#親要素からみた子要素の順序
		self.order = None

		#親要素
		self.parent = None

		#子要素
		self.children = list()

		#優先ラベル
		self.preferred_label = None

		#スキーマファイルのURI
		self.href = None

		#スキーマファイル中のID
		self.id = None



		#ノードの用途
		#ノードの名称
		#スキーマファイルを調査し設定
		self.__usage = None
		self.__name = None

		#ノードの日本語ラベル
		#名称リンクベースファイルを調査し設定
		self.__jp_label = None



	#href要素を設定する
	def set_href(self, href) :

		self.href = href
		self.id = href.split('#')[-1]


	#子ノードを追加する(順序付き)
	def append_child(self, child, order):
		child.order = order
		self.children.append(child)


	#スキーマファイルのURIを取得する
	def get_xsd_uri(self) :
		return self.href.split('#')[0]

	def get_id(self) :
		return self.id

	def set_usage(self, usage) :
		self.__usage = usage

	def get_usage(self) :
		return self.__usage

	def set_jp_label(self, jp_label) :
		self.__jp_label = jp_label

	def get_jp_label(self) :
		return self.__jp_label

	def get_href(self) :
		return self.href

	def set_name(self, name) :
		self.__name = name

	def get_name(self) :
		return self.__name


	def __lt__(self, other):
		return self.order < other.order



class JPStrLabelRecord():


	def __init__(self, id, role, jp_str):

		self.id = id
		self.role = role
		self.jp_str = jp_str

