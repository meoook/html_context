from html_context import HtmlContextParser

tags_params = {'button': {'value', }, }  # Optional: tags parameters to find useful text
tags_default = {'tooltip', }  # Optional: parameters to find useful text in all tags
parser = HtmlContextParser(tags_params, tags_default)
parser.data = '<div>Html data from file decoded utf8</div><div>Test<div>data</div>last</div>'  # Data from HTML file
list_of_items = parser.data
elements_tree = parser.tree

[print(elem) for elem in list_of_items]
print(elements_tree)

list_of_items[0]['text'] = 'Other'
# Build html file with new context but original structure
for item in list_of_items:
    print(f'{item["prefix"]}{item["text"]}', end='')  # can change on file.write()
