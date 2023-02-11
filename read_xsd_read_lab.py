import os
import glob
import shutil
import logging
import libxbrl



yuho_tree = libxbrl.XBRLStructureTree('.\\S10079H3\\XBRL\\PublicDoc\\jpcrp030000-asr-001_E31037-000_2015-12-31_01_2016-03-30_pre.xml')

rol_str = 'rol_ConsolidatedStatementOfIncome'

yuho_tree.read_xsd_file(rol_str)
yuho_tree.read_jp_lab_file(rol_str)
yuho_tree.show_tree(rol_str)

