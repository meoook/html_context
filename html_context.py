import re


class HtmlContextParser:
    """
        Control *valid* text data in HTML document
        Options:
          set TAG_PARAMS and TAG_PARAMS_DEFAULT to parse tag parameters for *valid* text
    """

    __INVALID_DATA_TAGS: set[str] = {'script', 'style'}
    __SELF_CLOSE_TAGS: set[str] = {'meta', 'link', 'hr', 'img', 'input', 'br'}
    __INLINE_TAGS: set[str] = {'b', 'u', 'i', 'strong'}   # TODO: Mb as items...
    __TAGS_PARAMS: dict[str, set[str]] = {}  # Params list of tag to parse as *valid* text
    __TAGS_PARAMS_DEFAULT: set[str] = set()  # Params that contain *valid* text for any tag

    def __init__(self, parse_options: dict[str, set[str]] = None, default_parameters: set[str] = None):
        self.__left_data: str = ''        # Not parsed data
        # Class props to return
        self.__dom_data: list[dict[str, str]] = []  # List of DOM-tree items (item where is *valid* text)
        self.__dom_tree: list[str] = []   # DOM tree of elements with context
        self.__warnings: list[str] = []   # DOM errors or parsing warnings
        # Element props while parsing
        self.__elem_dom: list[any] = [1, ]  # Element DOM tree *Unique* (index is always last item)
        self.__elem_prefix: str = ''        # Element technical text before *valid* text
        self.__elem_warning: str = ''       # Element warning (DOM tree errors like 'tag not closed')
        # Update tags parsing options
        if default_parameters:
            self.__set_tag_default_parse_options(default_parameters)
        if parse_options:
            self.__set_tag_parse_options(parse_options)

    @property
    def data(self) -> list[dict[str, str]]:
        """ Dict of DOM-tree items. Item is a tag where *valid* text (context without close tag). """
        return self.__dom_data

    @data.setter
    def data(self, value: str):
        """ Set data to parse as html (from file) and parse it """
        self.__left_data: str = value
        # Parse file while not EOF
        while self.__next_parse():
            pass

    @property
    def tree(self) -> list[str]:
        """ Return DOM-tree """
        return self.__dom_tree

    @property
    def warnings(self) -> list[str]:
        return self.__warnings

    def __next_parse(self) -> bool:
        """ Parse next part of file to find *valid* text """
        # Check for EOF
        if self.__end_of_file():
            return False
        # Check for invisible symbols at start
        if self.__cut_non_visible_start():
            return True
        # Try to parse next data as *valid* text
        _tag_data = re.match(r'[^<]+', self.__left_data)
        if not _tag_data:  # Data not found
            self.__tag_open_or_close()
        else:
            _text: str = _tag_data.group()
            _cut_idx: int = _tag_data.end()
            self.__elem_validate_and_add(_text, _cut_idx)
        return True

    def __elem_validate_and_add(self, text: str, cut_index: int, dom_suffix: str = '') -> None:
        """ Add *valid* text as elem or add *invalid* as prefix """
        if self.__is_text_valid(text):  # URL check
            _prefix = self.__elem_prefix_return(cut_index)  # Will null prefix
            _warning = self.__elem_warning_return()  # Will null warning
            _dom_tree = self.__elem_dom_string_return()  # Save element DOM position to DOM tree
            _dom_tree = f'{_dom_tree}:+{dom_suffix}' if dom_suffix else _dom_tree  # DOM tree for tag parameter
            _text = self.__cut_non_visible_end(text)  # Add non visible symbols to next prefix
            self.__dom_data.append({'dom': _dom_tree, 'text': _text, 'prefix': _prefix, 'warning': _warning})
        else:
            self.__cut_to_elem_prefix(cut_index)

    def __elem_prefix_return(self, cut_index: int) -> str:
        """ Return prefix and refresh data """
        _prefix = f'{self.__elem_prefix}'
        self.__elem_prefix = ''
        self.__left_data = self.__left_data[cut_index:]  # refresh not parsed data
        return _prefix

    def __elem_warning_return(self) -> str:
        """ Return warning and null it """
        _warning = f'{self.__elem_warning}'
        self.__elem_warning = ''
        return _warning

    def __elem_dom_string_return(self) -> str:
        """ Get tag and DOM tree of last element  """
        item_tree = ':'.join([str(tag) for tag in self.__elem_dom])
        self.__dom_tree.append(item_tree)
        return item_tree

    def __tag_open_or_close(self) -> None:
        """ Find what kind of tag is next """  # TODO: (check tag parameters for open tag)
        if self.__left_data.startswith('</'):
            _cut_idx = self.__left_data.find('>')
            if _cut_idx == -1:
                self.__data_broken()
            else:
                _close_tag: str = self.__left_data[2:_cut_idx]
                self.__cut_to_elem_prefix(_cut_idx + 1)
                # Validate tag name
                if re.match(r'[a-z]', _close_tag, re.IGNORECASE):
                    self.__tag_dom_close(_close_tag)
                else:
                    self.__warnings.append(f'close tag not html format - {_close_tag}')
        else:
            _html_tag = re.match(r'<([a-z]+)(>|/>|\s*)', self.__left_data, re.IGNORECASE)
            if _html_tag:
                _open_tag = _html_tag.group(1)
                _after_tag = _html_tag.group(2)
                _cut_idx = _html_tag.end()
                self.__cut_to_elem_prefix(_cut_idx)
                # When open any tag - add tag and it's first index to dom tree
                self.__elem_dom += [_open_tag, 1]
                # Control tag parameters, auto-close tag, get cut index
                if _after_tag == '/>':  # Close tag if self closed
                    self.__tag_dom_close(_open_tag)
                    if _open_tag not in self.__SELF_CLOSE_TAGS:
                        self.__warnings.append(f'tag {_open_tag} not in known self-close tags but ends with /')
                elif _open_tag in self.__INVALID_DATA_TAGS:
                    # Cut data inside non *valid* tags (leave </tag_name> to close tag on next iteration)
                    self.__cut_or_eof(f'</{_open_tag}')
                elif _open_tag in self.__SELF_CLOSE_TAGS:  # No need / for *self-close* tag (like <br>)
                    self.__tag_dom_close(_open_tag)
                    if _after_tag != '>':
                        self.__tag_parse_params(_open_tag, ignore_params=True)
                        self.__warnings.append(f'self-close tag {_open_tag} have parameters')
                elif _after_tag != '>':
                    self.__tag_parse_params(_open_tag)
            else:
                # tags like <!doctype> or unknown tags <?> ignored in DOM tree
                self.__cut_or_eof('>')

    def __tag_parse_params(self, tag_name: str, ignore_params: bool = False) -> None:
        """ Parse tag parameters till end tag """
        while self.__tag_param_next_or_end(tag_name, ignore_params):
            pass

    def __tag_param_next_or_end(self, tag_name: str, ignore_params) -> bool:
        """ Parse next tag parameter or end tag """
        _param = re.match(r'([a-z-_]+)\s*=\s*', self.__left_data, re.IGNORECASE)
        if _param:
            # common parameter
            _param_name = _param.group(1)
            _cut_idx = _param.end()
            self.__cut_to_elem_prefix(_cut_idx)
            # self.__tag_param_add_or_cut(tag_name, _param_name, ignore_params)
            return self.__tag_param_add_or_cut(tag_name, _param_name, ignore_params)
        elif self.__left_data.startswith('>') or self.__left_data.startswith('/>'):
            # common end of tag
            self.__cut_or_eof('>')
            self.__cut_non_visible_start()
        else:
            # data broken or unknown template - but try to find tag end '>'
            self.__warnings.append(f'wrong html parameter in {tag_name}')
            self.__elem_warning = 'unknown tag parameters structure'
            self.__cut_or_eof('>')
        return False

    def __tag_param_add_or_cut(self, tag_name: str, param_name: str, ignore_params: bool) -> bool:
        """ Check parameter and add it as elem or add to prefix (return True if no errors) """
        # Find parameter value and it's cut index
        _next_char = self.__left_data[0]
        if _next_char == '"':  # double quote
            _value = re.match(r'"\s*([^"]*?)"', self.__left_data)
        elif _next_char == "'":  # single quote
            _value = re.match(r"'\s*([^']*?)'", self.__left_data)
        else:  # space as quote/delimiter or tag ends
            _value = re.match(r'([^\s]+?)[\s>]', self.__left_data)

        if _value:
            # check parameter to add as elem (don't change order !)
            if self.__left_data.startswith('<'):
                self.__warnings.append(f'wrong parameter value in tag {tag_name}')
                self.__cut_or_eof('>')
            elif not ignore_params and param_name in self.__TAGS_PARAMS_DEFAULT or \
                    tag_name in self.__TAGS_PARAMS.keys() and param_name in self.__TAGS_PARAMS[tag_name]:
                # cut quote and invisible symbols at start
                _cut_idx = _value.start(1)
                self.__cut_to_elem_prefix(_cut_idx)
                # add item
                _end_idx = _value.end(1) - _cut_idx
                _param_value: str = _value.group(1)
                self.__elem_validate_and_add(text=_param_value, cut_index=_end_idx, dom_suffix=param_name)
                # cut quote and invisible symbols at end (of parameter)
                if _next_char in ['\'', '"']:
                    self.__cut_to_elem_prefix(1)
            else:
                _cut_idx = _value.end() if _next_char in ['\'', '"'] else _value.end(1)
                self.__cut_to_elem_prefix(_cut_idx)
            self.__cut_non_visible_start()
            return True
        else:
            self.__warnings.append(f'tag {tag_name} parameters quote error')
            self.__cut_or_eof('>')
        return False

    def __tag_dom_close(self, tag_name: str) -> None:
        """ Handle closing tag - update tag tree """
        if tag_name in self.__elem_dom:
            if self.__elem_dom[-2] == tag_name:
                self.__elem_dom = self.__elem_dom[:-2]
            else:
                # tag not at the end of a tree (tree cut error)
                _fix_dom_tree_cut_deep = len(self.__elem_dom) - 1 - self.__elem_dom[::-1].index(tag_name)
                self.__elem_dom = self.__elem_dom[:_fix_dom_tree_cut_deep]  # Cut DOM deep
                self.__elem_warning = 'previous tag was not closed'
                self.__warnings.append(f'dom tree error - tag before {tag_name} was not closed')
            self.__elem_dom[-1] += 1  # increment index for next child
        else:
            # close tag not found in tree (tree error)
            self.__warnings.append(f'dom tree error - close tag {tag_name} have no open tag')

    def __data_broken(self):
        """ For critical errors - save left data to EOF """
        _cut_idx = len(self.__left_data)
        self.__cut_to_elem_prefix(_cut_idx)
        _prefix = self.__elem_prefix_return(_cut_idx)
        _data_tail = {'dom': 'EOF', 'text': _prefix, 'prefix': _prefix, 'warning': 'data broken'}
        self.__dom_data.append(_data_tail)  # Add left data to return data as 'EOF'
        self.__warnings.append(f'data broken - {_cut_idx} bytes left not parsed')

    def __end_of_file(self) -> bool:
        """ Check for EOF """
        if not self.__left_data:  # no more data to parse
            if self.__dom_data and self.__dom_data[-1]['dom'] != 'EOF':
                _prefix = self.__elem_prefix_return(0)
                _data_tail = {'dom': 'EOF', 'text': '', 'prefix': _prefix, 'warning': 'end of file'}
                self.__dom_data.append(_data_tail)  # Add left data to return data as 'EOF'
            return True
        return False

    def __cut_to_elem_prefix(self, cut_index: int) -> None:
        """ Update prefix and left data by cut index (of left data) - it's primary cut function """
        self.__elem_prefix += self.__left_data[:cut_index]
        self.__left_data = self.__left_data[cut_index:]  # refresh not parsed data

    def __cut_or_eof(self, value: str) -> None:
        """ Find substring index or data broken """
        _index: int = self.__left_data.find(value)
        if _index == -1:
            self.__data_broken()
        elif len(value) == 1:  # Add '>' to prefix
            self.__cut_to_elem_prefix(_index + 1)
        else:
            self.__cut_to_elem_prefix(_index)

    def __cut_non_visible_start(self) -> bool:
        """ Add invisible symbols at start to prefix """
        _start_with_non_visible = re.match(r'\s+(.*)', self.__left_data)
        if _start_with_non_visible:
            _cut_idx = _start_with_non_visible.start(1)
            self.__cut_to_elem_prefix(_cut_idx)
            return True
        return False

    def __cut_non_visible_end(self, text: str) -> str:
        """ Add invisible symbols at end to next elem prefix """
        _validate = re.fullmatch(r'(.*?)\s+$', text)
        if _validate:
            _index = _validate.end(1)
            self.__elem_prefix += text[_index:]  # Prefix for next elem (elem_prefix must be empty at this moment)
            return text[:_index]
        return text

    # ==============================
    # TODO: SETTER - params_default
    def __set_tag_default_parse_options(self, parameters: set[str]) -> None:
        """ Update what parameters to parse as *valid* text for any tag """
        if self.__TAGS_PARAMS:
            raise ValueError('Call order error: change default options before tag options were set')
        self.__TAGS_PARAMS_DEFAULT |= parameters

    # TODO: SETTER - params_tags
    def __set_tag_parse_options(self, tags_options: dict[str, set[str]]) -> None:
        """ Update in what tags parse parameters as *valid* text """
        if isinstance(tags_options, dict):
            _untestable_tags = self.__INVALID_DATA_TAGS | self.__SELF_CLOSE_TAGS
            for _tag_name in tags_options.keys():
                if _tag_name not in _untestable_tags:
                    _params = tags_options[_tag_name] - self.__TAGS_PARAMS_DEFAULT   # Remove tag params if in defaults
                    if _params:
                        self.__TAGS_PARAMS |= {_tag_name: _params}

    @staticmethod
    def __is_text_valid(text: str) -> bool:
        """ Validate text """
        try:  # Float check
            float(text)
            return False
        except ValueError:
            pass
        _text = text.strip()
        if re.match(r'[0-9 ,./<>?;\'\\":|\[\]{}!@#$%^&*()+=-_]+$', _text):  # only numbers and symbols
            return False
        if ' ' in _text:  # Text with space is *valid*
            return True
        elif _text and re.match(r'[^.:/\s]+.$', _text):  # empty, URL like or technical
            return True
        else:
            return False
