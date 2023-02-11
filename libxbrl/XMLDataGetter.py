import requests
from bs4 import BeautifulSoup
import time
import logging


logger = logging.getLogger(__name__)



#サーバ上のXMLファイルをキャッシュする
class XMLDataGetter() :

        data_cache = {}

        @classmethod
        def get(cls, data_path):


                soup = None

                if data_path in cls.data_cache :

                        logger.debug('get xml from cache')
                        soup = cls.data_cache[data_path]


                elif data_path.startswith('http') :

                        soup = cls.__get_from_html_path(data_path)

                else :

                        soup = cls.__get_from_local_path(data_path)

                return soup

        @classmethod
        def __get_from_html_path(cls, url):

                logger.info('get xml from : ' + url)

                r = requests.get(url)
                soup = BeautifulSoup(r.content, 'xml')
                r.close()

                time.sleep(1.0)

                cls.data_cache[url] = soup

                return soup

        @classmethod
        def __get_from_local_path(cls, local_path):

                logger.info('get xml from : ' + local_path)

                fin = open(local_path, 'rb')
                bdata = fin.read()
                soup = BeautifulSoup(bdata, 'xml')
                fin.close()


                cls.data_cache[local_path] = soup

                return soup



