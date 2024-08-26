#!/usr/bin/env python3
#
# Note: some of this is hacky AF 
# it's a quick & dirty script with emphasis
# on dirty.
#
# Query a set of recipes from the old recipebook.bentasker.co.uk site
# turn them into markdown and write into Nikola
#
# Note: this script will no longer do anything as the migration has been
# completed - for reference purposes only
#
'''
Copyright (c) 2024 B Tasker

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''



import os
import sys
import re
import requests

from lxml import etree
from markdownify import markdownify as md


def extract_page(url):
    
    details = {
        "categories" : [],
        "keywords" : [],
        "timings" : [
            False,
            False,
            False,
            ]
        }
    r = requests.get(url)
    
    # For some reason, etree doesn't like target=_blank in links, so strip them
    altered = r.text.replace("target=_blank","").replace('target="_blank"',"")
    
    
    parser = etree.HTMLParser(recover=True)
    root = etree.fromstring(altered, parser=parser)
    
    
    ''' Notes
    Publish date is in a div with ID called artInfo **but** this is shared with categories. However, there's also a meta element with itemprop datePublished

    Categories are in a's with class catLink



    Recipe content is in a div with id wrapper

    If a recipe image is set, it's in an img tag with class="recipeimage" and itemprop="image"

    Description is in div with id description

    Cooking time IDs are under

    * preptime
    * oventime
    * tottime

    The main category is in a span with itemprop recipeCategory

    Ingredients are in a UL under a div with class ingredients

    Method steps are in an ol under a div with id method

    Based on is in a ul under a div with class isbasedupon

    Keywords are in spans with class contentkeyword (though there's a link under that). Probably easiest to grab from the meta with itemprop keywords 
    (it's a comma seperated list)

    '''    

    
    
    e = root.find('.//h1[@itemprop="headline"]')
    if e is not None:
        details['title'] = e.text   
    
    e = root.find('.//meta[@itemprop="datePublished"]')
    if e is not None:
        details['published'] = e.attrib['content']
        
    e = root.find('.//meta[@itemprop="keywords"]')
    if e is not None:
        details['keywords'] = e.attrib['content'].split(",")
        
    e = root.findall('.//a[@class="catLink"]')
    for i in e:
        details['categories'].append(i.text.lower())
        
    e = root.find('.//span[@itemprop="recipeCategory"]')
    if e is not None:
        details['mainCategory'] = e.text.lower().strip()
        
    e = root.find('.//img[@class="recipeimage"]')
    if e is not None:
        details['image'] = e.attrib['src'].replace("https://static1.bentasker.co.uk", "")
        
    e = root.find('.//div[@class="description"]')
    if e is not None:    
        details['description'] = etree.tostring(e, method='xml')
 
    timings = [
            [0, 'prep'],
            [1, 'oven'],
            [2, 'tot']
        ]
 
    for t in timings:
        e = root.find(f'.//span[@id="{t[1]}timeval"]')
        if e is not None:    
            details['timings'][t[0]] = e.text
 
    e = root.find('.//div[@class="ingredients"]//ul')
    if e is not None:    
        details['ingredients'] = etree.tostring(e)    
    
    e = root.find('.//div[@id="method"]')
    if e is not None:    
        details['method'] = etree.tostring(e)
        
    e = root.find('.//div[@itemprop="isBasedOn"]')
    if e is not None:    
        details['basedon'] = etree.tostring(e)        
    
    
    # slugify the title and category
    for i in [["title", "slug"], ["mainCategory", "cat-slug"]]:
        # replace spaces
        slg1 = details[i[0]].lower().replace(" ", "-")
        # Strip any char not in the set
        details[i[1]] = re.sub("[^abcdefghijklmnopqrstuvwxyz0123456789\-]+", "", slg1)
    
    return details
    
    
def build_markdown(details):
    ''' Take the details dict and build the markdown page template
    '''
            
    # Build the tagset
    tags = []
    for t in details['keywords'] + details['categories']:
        t_l = t.lower()
        if t_l not in tags:
            tags.append(t_l)


    # Construct the YAML frontmatter
    s = [
        '---',
        f'title: {details["title"]}',
        f'slug: {details["slug"]}',
        'type: text',
        'author: Ben Tasker',        
        f'date: {details["published"]}',
        f'tags: {tags}',
        f'category: {details["mainCategory"]}',
        ]
    
    if 'image' in details:
        s.append(f'previewimage: {details["image"]}')
    
    
    s.append('---')
    s.append("")    
    
    # Insert the description
    s.append(md(details['description']))
    s.append("")
    s.append("<!-- TEASER_END -->")
    s.append("")
    
    # Cooking timings
    if any(details['timings']):
        s.append('<a name="cooking_duration"></a>')
        s.append("")
        s.append('### Cooking Time')
        
        
        prep_time = details['timings'][0] if details['timings'][0] else ""
        cook_time = details['timings'][1] if details['timings'][1] else ""
        totl_time = details['timings'][2] if details['timings'][2] else ""
        
        # Create a HTML table so that we can then convert it into markdown
        html = f"""<table>
          <tr><th>Prep</th><th>Cooking</th><th>Total</th></tr>
          <tr><td>{prep_time}</td><td>{cook_time}</td><td>{totl_time}</td></tr>
        </table>
        """
    
        # Now markdown and append it
        s.append(md(html))
        s.append("")

    # There are pages (like the roast timing page) that don't have an ingredients section
    if "ingredients" in details:
        s.append('<a name="ingredients"></a>')
        s.append("")
        s.append('### Ingredients')
        s.append(md(details['ingredients']))
    
    # The rice cooker timing page doesn't have a method section
    if "method" in details:
        s.append('<a name="method"></a>')
        s.append("")
        s.append('### Method')
        s.append(md(details['method']))
        
    if "basedon" in details:
        s.append('<a name="based_on"></a>')
        s.append("")
        s.append('### Based On')
        s.append(md(details['basedon']))        
    
    
    # Collapse into a single string and return
    return '\n'.join(s)


def build_nginx_redirect(oldpath, newpath):
    ''' Generate a Nginx location block to redirect from old to new
    '''
    
    s = [
        "location = {} {{".format(oldpath),
        "   return 301 {};".format(newpath),
        "}"              
        ]
    return '\n'.join(s)


# func main

# Get a list of pages
srch = {
    "term":"page- matchtype:url domain:recipebook.bentasker.co.uk ext:html",
    "type":"DOC"
    }

# Run the search
r = requests.post(
    "https://filesearch.bentasker.co.uk/search",
    json = srch
    )

BASE_PATH = os.path.join(os.path.dirname(__file__), "../../posts/")
nginx_redirs = []

# Iterate through the results
for result in r.json()['results']:
    url = result['key']
    print(f"processing {url}")
    details = extract_page(url)
    markdown = build_markdown(details)
    
    # Calculate where we should be writing it
    dir_path = os.path.join(BASE_PATH, details["cat-slug"])
    file_path = os.path.join(dir_path, f"{details['slug']}.md")
    
    # Create the directory
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    
    # Write the file
    with open(file_path, 'w') as fh:
        fh.write(markdown)
    
    redir = build_nginx_redirect(
                result['path'], 
                f'/posts/{details["cat-slug"]}/{details["slug"]}.html'
            )
    nginx_redirs.append(redir)
    
with open("nginx_redirs", "w") as fh:
    fh.write("\n".join(nginx_redirs))
    
