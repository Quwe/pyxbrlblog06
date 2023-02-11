import requests
import time
import sqlite3
import os

from .XBRLPath import get_xbrl_dir_path
from .XBRLPath import get_xbrl_file_path

class EdinetDocumentInfoRecord() :


	def __init__(self, seq_number, \
				doc_id, \
				edinet_code, \
				sec_code, \
				jcn, \
				filer_name, \
				fund_code, \
				ordinance_code, \
				form_code, \
				doc_type_code, \
				period_start, \
				period_end, \
				submit_date_time, \
				doc_description, \
				issuer_edinet_code, \
				subject_edinet_code, \
				subsidiary_edinet_code, \
				current_report_reason, \
				parent_doc_id, \
				ope_date_time, \
				withdrawal_status, \
				doc_info_edit_status, \
				disclosure_status, \
				xbrl_flag, \
				pdf_flag, \
				attach_doc_flag, \
				english_doc_flag, \
				csv_flag, \
				legal_status, \
				json_date):


		self.__seq_number=seq_number
		self.__doc_id=doc_id
		self.__edinet_code=edinet_code
		self.__sec_code=sec_code
		self.__jcn=jcn
		self.__filer_name=filer_name
		self.__fund_code=fund_code
		self.__ordinance_code=ordinance_code
		self.__form_code=form_code
		self.__doc_type_code=doc_type_code
		self.__period_start=period_start
		self.__period_end=period_end
		self.__submit_date_time=submit_date_time
		self.__doc_description=doc_description
		self.__issuer_edinet_code=issuer_edinet_code
		self.__subject_edinet_code=subject_edinet_code
		self.__subsidiary_edinet_code=subsidiary_edinet_code
		self.__current_report_reason=current_report_reason
		self.__parent_doc_id=parent_doc_id
		self.__ope_date_time=ope_date_time
		self.__withdrawal_status=withdrawal_status
		self.__doc_info_edit_status=doc_info_edit_status
		self.__disclosure_status=disclosure_status
		self.__xbrl_flag=xbrl_flag
		self.__pdf_flag=pdf_flag
		self.__attach_doc_flag=attach_doc_flag
		self.__english_doc_flag=english_doc_flag
		self.__csv_flag=csv_flag
		self.__legal_status=legal_status
		self.__json_date=json_date


	def get_doc_id(self) :
		return self.__doc_id

	def get_edinet_code(self) :
		return self.__edinet_code

	def get_filer_name(self) :
		return self.__filer_name

	def get_doc_description(self) :
		return self.__doc_description


def search_yuho_xbrl_document(edinet_code) :

	edinet_document_info_record_list = list()


	conn = sqlite3.connect('edinetfile.db')
	conn.row_factory = sqlite3.Row
	cur = conn.cursor()


	cur.execute('SELECT * FROM edinet_document \
			WHERE edinet_code=? AND doc_type_code=? AND xbrl_flag=?',\
			 (edinet_code,'120', '1'))


	row = cur.fetchone()
	while row != None :

		search_result = EdinetDocumentInfoRecord( row['seq_number'],\
						row['doc_id'],\
						row['edinet_code'],\
						row['sec_code'],\
						row['jcn'],\
						row['filer_name'],\
						row['fund_code'],\
						row['ordinance_code'],\
						row['form_code'],\
						row['doc_type_code'],\
						row['period_start'],\
						row['period_end'],\
						row['submit_date_time'],\
						row['doc_description'],\
						row['issuer_edinet_code'],\
						row['subject_edinet_code'],\
						row['subsidiary_edinet_code'],\
						row['current_report_reason'],\
						row['parent_doc_id'],\
						row['ope_date_time'],\
						row['withdrawal_status'],\
						row['doc_info_edit_status'],\
						row['disclosure_status'],\
						row['xbrl_flag'],\
						row['pdf_flag'],\
						row['attach_doc_flag'],\
						row['english_doc_flag'],\
						row['csv_flag'],\
						row['legal_status'],\
						row['json_date'])


		edinet_document_info_record_list.append(search_result)

		row = cur.fetchone()


	cur.close()
	conn.close()

	return edinet_document_info_record_list


def download_edinet_xbrl(doc_id) :


	download_result = False

	params = {
		'type' : 1
	}


	url = 'https://disclosure.edinet-fsa.go.jp/api/v1/documents/' + doc_id
	retry_count = -1
	while retry_count < 10 :

		retry_count = retry_count + 1

		time.sleep(2.0)

		try:

			res = requests.get(url, \
					params=params, \
					verify=True, \
					timeout = 120.0)

		except requests.exceptions.RequestException as e:

			print('requests error' + str(e) )

			time.sleep(10.0)
			continue


		if res.status_code != 200 :

			print('status_code:' + res.status_code)
			res.close()
			time.sleep(10.0)
			continue

		if res.headers['content-type'] != 'application/octet-stream' :

			print('content-type:' + res.headers['content-type'])

			res.close()
			time.sleep(10.0)
			continue



		#XBRLをローカルに保存する
		if not os.path.exists( get_xbrl_dir_path() ) :
			os.makedirs( get_xbrl_dir_path() )

		with open(get_xbrl_file_path(doc_id), 'wb') as f :
			for chunk in res.iter_content(chunk_size=1024) :
				f.write(chunk)

		res.close()


		download_result = True

		break


	return download_result
