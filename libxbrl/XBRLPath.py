import os

def get_xbrl_dir_path() :

	return '.' + os.sep + 'xbrl'


def get_xbrl_file_path(doc_id) :


	return os.path.join( get_xbrl_dir_path(), doc_id + '.zip' )

