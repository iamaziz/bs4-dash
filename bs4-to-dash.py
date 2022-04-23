"""
download the documentation of 'Beautiful Soup 4' and generate a 'docset' (offline documentation) for Dash/Zeal/Velocity

based on: https://github.com/iamaziz/bs4-dash by @iamaziz (Aziz Alto)
rewritten for Python 3 by: @iNtEgraIR2021 (Petra Mirelli) 2021-2022

"""

import json
import sys
import sqlite3
import re
from pathlib import Path
from pprint import pprint

from urllib.request import urlretrieve # needed for python3 support -> see https://stackoverflow.com/a/21171861 

from bs4 import BeautifulSoup as bs
import requests

# CONFIGURATION
docset_name = 'Beautiful_Soup_4.docset'
output = docset_name + '/Contents/Resources/Documents/'

root_url = 'https://www.crummy.com/software/BeautifulSoup/bs4/doc/'

p = Path(output) / Path('crummy.com/bs4/')
p.mkdir(parents=True, exist_ok=True) # create directory tree required for docset generation
output = str(p) + '/'

# add icon
icon = 'https://upload.wikimedia.org/wikipedia/commons/7/7f/Smile_icon.png'
urlretrieve(icon, docset_name + "/icon.png")

def update_db(name, path):

  typ = 'func'

  cur.execute('CREATE TABLE IF NOT EXISTS searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);')
  cur.execute("SELECT rowid FROM searchIndex WHERE path = ?", (path,))
  fetched = cur.fetchone()
  if fetched is None:
      cur.execute('INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)', (name, typ, path))
      print('DB add >> name: %s, path: %s' % (name, path))
  else:
      print("record exists")

def get_css_file(file_name):
    file_url = root_url + str(file_name)
    print(f" downloading css file {file_url}")

    content_temp = str(requests.get(file_url).text).strip()
    content_temp = re.sub(r'(?im)[\r\t\n]+','',content_temp)

    import_pattern = re.compile(r'(?im)(\@import url\()([\'\"]+)([^\'\"]+)([\'\"]+)\)')
    import_matches = re.findall(import_pattern, content_temp)
    for import_match in import_matches:
      file_name = str(import_match[2]).strip().strip("'").strip('"')
      #print(file_name)
      if len(file_name) > 0:
        content_temp += str(get_css_file('_static/'+file_name))

    content_temp = re.sub(import_pattern,'',content_temp)
    content_temp = re.sub(r'(?m)\/\*[^*]*\*+([^\/*][^*]*\*+)*\/','',content_temp) # remove css comments -> based on: https://stackoverflow.com/a/9329651
    
    while '  ' in content_temp:
      content_temp = re.sub(r'(?m)( ){2}',' ',content_temp).strip()
    
    return content_temp

def get_js_file(file_name):
    file_url = root_url + str(file_name)
    print(f" downloading js file {file_url}")

    content_temp = str(requests.get(file_url).text).strip()
    content_temp = re.sub(r'(?im)[\r\t\n]+','',content_temp)

    #content_temp = re.sub(r'(?m)\/\*[^*]*\*+([^\/*][^*]*\*+)*\/','',content_temp) # remove js comments -> based on: https://stackoverflow.com/a/9329651
    
    while '  ' in content_temp:
      content_temp = re.sub(r'(?m)( ){2}',' ',content_temp).strip()
    
    return content_temp

def add_urls():

  # start souping index_page
  data = str(requests.get(root_url).text).strip()
  soup = bs(data, features='html.parser')

  css_links = soup.select('head > link[href$=".css"]') # download and minimize css 
  if len(css_links) > 0:
    css_content = ''
    for css_link in css_links:
      css_href = str(css_link.get('href')).strip()
      css_content += get_css_file(css_href)

    if len(css_content) > 0:
      css_links[0].replace_with(bs('<style>'+str(css_content)+'</style>', features='html.parser').style)
      css_links = soup.select('head > link[href$=".css"]')
      for css_link in css_links:
        css_link.decompose()

  js_scripts = soup.select('head > script') # download and minimize js 
  if len(js_scripts) > 0:
    js_content = ''
    for js_script in js_scripts:
      js_src = str(js_script.get('src')).strip()
      js_content += get_js_file(js_src)

    if len(js_content) > 0:
      #with open(output + 'script.js','w+',encoding='utf-8') as fh:
      #  fh.write(str(js_content))

      js_scripts[0].replace_with(bs('<script type="text/javascript" id="documentation_options" data-url_root="./">'+str(js_content)+'</script>', features='html.parser').script)
      
      js_scripts = soup.select('head > script')
      for js_script in js_scripts:
        if js_script.get('src') != None:
          js_script.decompose()

  img_tags = soup.select('img') #download images
  for img_tag in img_tags:
    img_src = str(img_tag.get('src')).strip()
    if len(img_src.replace('None','')) > 1:
      img_file_name = img_src.split('/')[-1]
      img_url = root_url+img_src

      print(f"downloading image '{img_url}' ")
      with open(output+img_file_name, 'wb') as f:
          f.write(requests.get(img_url).content)
      
      img_tag['src'] = img_file_name

  index_link = soup.select('link[rel="index"]') # remove nav bar entry of empty index page
  if len(index_link) == 1:
    index_link[0].decompose()

  index_a = soup.select('a[href$="genindex.html"]') # remove references of empty index page
  if len(index_a) > 0:
    for a_temp in index_a:
      a_temp.decompose()

  search_link = soup.select('link[rel="search"]')
  if len(search_link) == 1:
    search_link[0].decompose()

  search_box = soup.select('#searchbox')
  if len(search_box) == 1:
    search_box[0].string = '' # remove search box -> relies on sphinx backend

  with open(output + 'index.html','w+',encoding='utf-8') as fh:
    fh.write(str(soup.prettify()))

  # collected needed pages and their urls
  for link in soup.select('.section h3'):
    path = str(link.select('.headerlink')[0].get('href')).replace('None','').strip()
    link.select('.headerlink')[0].decompose()
    name = re.sub(r'(?im)<[^>]+>','',str(link.text).strip().replace('\n', ''))

    if len(path) > 1 and name is not None:
      path = 'crummy.com/bs4/index.html' + path
      update_db(name, path)

def add_infoplist():
  CFBundleIdentifier = 'bs4'
  CFBundleName = 'Beautiful Soup 4'
  DocSetPlatformFamily = 'bs4'

  info = " <?xml version=\"1.0\" encoding=\"UTF-8\"?>" \
         "<plist version=\"1.0\"> " \
         "<dict> " \
         "    <key>CFBundleIdentifier</key> " \
         "    <string>{0}</string> " \
         "    <key>CFBundleName</key> " \
         "    <string>{1}</string>" \
         "    <key>DocSetPlatformFamily</key>" \
         "    <string>{2}</string>" \
         "    <key>dashIndexFilePath</key>" \
         "    <string>{3}</string>" \
         "    <key>isDashDocset</key>" \
         "</dict>" \
         "</plist>".format(CFBundleIdentifier, CFBundleName, DocSetPlatformFamily, 'crummy.com/bs4/index.html')
  open(docset_name + '/Contents/info.plist', 'wb').write(info.encode('utf-8'))

def add_meta():
  meta_dict = {
    "extra": {
        "indexFilePath": "crummy.com/bs4/index.html" # using fake url to keep path as short as possible to avoid Windows OS bug
    },
    "name": "Beautiful Soup",
    "title": "Beautiful Soup"
  }

  with open(docset_name + '/meta.json','w+',encoding='utf-8') as fh:
    fh.write(str(json.dumps(meta_dict, indent=4)))


db = sqlite3.connect(docset_name + '/Contents/Resources/docSet.dsidx')
cur = db.cursor()

cur.execute('CREATE TABLE IF NOT EXISTS searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);')
cur.execute('CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);')

try:
    cur.execute('DROP TABLE searchIndex;')
except Exception as e:
    print(e)
    cur.execute('CREATE TABLE IF NOT EXISTS searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);')
    cur.execute('CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);')


# start
add_urls()

add_infoplist()

add_meta()

# commit and close db
db.commit()
db.close()
