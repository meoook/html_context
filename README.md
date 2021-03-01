# HTML context parser

* Version: 0.01.1
* Description: Find **useful text** in HTML. Main idea to build html file with original structure after text change.
* Author: [meok][author]
* Depends: no (native)

## Inside package

- [x] Parse HTML or HTML templates documents
- [ ] Add more templates variants for normal parse
- [x] Get **useful text** text from tags
- [x] Mark text with unique DOM path/mark
- [x] Option to lookup tags parameters for **useful text**
- [x] Warnings if errors in DOM structure
 or templates and get tags context where text contained.
# Example

```python
from html_context import HtmlContextParser

tags_params = {'button': {'value', }, }  # Optional: tags parameters to find useful text
tags_default = {'tooltip', }  # Optional: parameters to find useful text in all tags
parser = HtmlContextParser(tags_params, tags_default)
parser.data = '<div>Html data from file decoded utf8</div><div>Test<div>data</div>last</div>'  # Data from HTML file
list_of_items = parser.data
elements_tree = parser.tree

[print(item) for item in list_of_items]
# {'dom': '1:div:1', 'text': 'Html data from file decoded utf8', 'prefix': '<div>', 'warning': ''}
# {'dom': '2:div:1', 'text': 'Test', 'prefix': '</div><div>', 'warning': ''}
# {'dom': '2:div:1:div:1', 'text': 'data', 'prefix': '<div>', 'warning': ''}
# {'dom': '2:div:2', 'text': 'last', 'prefix': '</div>', 'warning': ''}
# {'dom': 'EOF', 'text': '</div>', 'prefix': '</div>', 'warning': 'end of file'}

print(elements_tree)
# ['1:div:1', '2:div:1', '2:div:1:div:1', '2:div:2']

# Change/update context 
list_of_items[0]['text'] = 'Updated text'
# Build updated html file with new context but original structure
for item in list_of_items:
    print(f'{item["prefix"]}{item["text"]}', end='')  # change on file.write()
# <div>Updated text</div><div>Test<div>data</div>last</div></div>
```

# Release notes

| version | date     | changes                                                            |
| ------- | -------- | ------------------------------------------------------------------ |
| 0.01.02 |     *    | Return values to ABS data types                                    |
| 0.01.01 | 02.03.21 | Realise                                                            |

[author]: <https://bazha.ru> "meok home page"
