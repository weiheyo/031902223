import copy
# import pstats

from pypinyin import lazy_pinyin
import sys

# 存储变形后的敏感词的原形
real_keyword = {}
# pianpangs = []


def read_keywords(file_path):
    with open(file_path, encoding='utf-8') as keyword_list:
        return keyword_list.read().splitlines()


def read_article(file_path):
    with open(file_path, encoding='utf-8') as article:
        return article.read()


def write_ans(file_path, ans_list):
    with open(file_path, 'w', encoding='utf-8') as ans:
        ans.write('total: ' + str(ans_list[0]) + '\n')
        for word in ans_list:
            if isinstance(word, int):
                continue
            # 按格式输出
            ans.write(
                'Line' + str(word['line']) + ': ' + '<' + real_keyword[word['keyword']] + '> ' + word['match'] + '\n')


class DFA:

    def __init__(self, keyword_list):
        self.state_event_dict = self._generate_state_event_dict(keyword_list)

    # 匹配
    def match(self, content: str):
        # 引入got_one_end达成避免在出现falungong时同时检测出falung与falungong的错误现象的目的，pop掉falung,使用列表是为了方便在函数间传递
        got_one_end = [False]
        match_list = [0]
        state_list = []
        temp_match_list = []
        # 默认第一行开始
        which_line = 1
        for char_pos, char in enumerate(content):
            is_pin = False
            if char == '\n':
                which_line += 1
            # 英文转小写
            if 65 <= ord(char) <= 90:
                char = char.lower()
                # print(char+"here!!!\n")
            # 汉字转拼音（除了偏旁）
            if 19968 <= ord(char) <= 40869:
                # if char not in pianpangs:
                char = lazy_pinyin(char)[0]
                is_pin = True
            if is_pin:
                for index, char_part in enumerate(char):
                    # 对拼音的最后一个字符进行判定，若符合，则将原本汉字存入错误文本中
                    if index == len(char) - 1:
                        self._match_part(char_part, char_pos, match_list, state_list, temp_match_list, content,
                                         which_line,
                                         got_one_end)
                        continue
                    # 对拼音除最后一个字符之外的每一个都进行判定，输入None是为了不把拼音存入错误文本中
                    if self._match_part(char_part, index, match_list, state_list, temp_match_list, None, which_line,
                                        got_one_end) == -1:
                        break
            else:
                self._match_part(char, char_pos, match_list, state_list, temp_match_list, content, which_line,
                                 got_one_end)
        return match_list

    def _match_part(self: str, char, char_pos, match_list, state_list, temp_match_list, content, which_line,
                    got_one_end):
        # 如果是某关键词首字母则从开头头开始
        # temp_match_list的match的值是变形后敏感词文本，keyword是未变形的敏感词文本
        if char in self.state_event_dict:
            state_list.append(self.state_event_dict)
            temp_match_list.append({
                "line": which_line,
                "match": "",
                "keyword": ""
            })
        for index, state in enumerate(state_list):

            # 排除特殊字符
            if char in ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', ';', '-', '=', '[', ']', '\\', '\'',
                        ',', '.', '/', '~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '+', '_', '{', '}',
                        '|', ':', '"', '<', '>', '?', '…', '·', '*', '？', '【', '】', '《', '》', '：', '“', '，',
                        '。', '、', '/', ' ', '￥', '！']:
                # 也可以使用排除掉汉字、英文字母的方法
                # if not 19968 <= ord(char) <= 40869 and not 97 <= ord(char) <= 122 and not 65 <= ord(char) <= 90:
                if content:
                    temp_match_list[index]["match"] += content[char_pos]
                # 直接跳过字符到下一个
                continue
            if char in state:
                # 进入下一个关键字的字符
                state_list[index] = state[char]
                # 大写字母保存在错误文本，原关键词保存在正确文本
                if content:
                    temp_match_list[index]["match"] += content[char_pos]
                temp_match_list[index]["keyword"] += char

                if state[char]["is_end"]:
                    match_list.append(copy.deepcopy(temp_match_list[index]))
                    match_list[0] += 1
                    if len(state[char].keys()) == 1:
                        # 这一步是排除未完整检测完如 falungong 便将falung加入检测出的列表中的错误
                        if got_one_end[0]:
                            match_list.pop()
                            match_list.pop()
                            match_list[0] -= 1
                            match_list.append(copy.deepcopy(temp_match_list[index]))
                            state_list.pop(index)
                            temp_match_list.pop(index)
                            got_one_end[0] = False
                        else:
                            state_list.pop(index)
                            temp_match_list.pop(index)
                        continue
                    # 比如出现falungong，该代码是为了避免同时检测出falung与falungong，pop掉falung
                    got_one_end[0] = True
            else:
                state_list.pop(index)
                temp_match_list.pop(index)
                return -1

    @staticmethod
    def _generate_state_event_dict(keyword_list: list):
        state_event_dict = {}
        # 先对关键字列表进行排序，加速接下来构建存储结构的速度
        keyword_list.sort()
        for keyword in keyword_list:
            current_dict = state_event_dict
            length = len(keyword)
            for index, char in enumerate(keyword):
                # 字符不在字典里
                if char not in current_dict:
                    next_dict = {"is_end": False}
                    # 加入字典中
                    current_dict[char] = next_dict
                    current_dict = next_dict
                # 字符在字典里
                else:
                    next_dict = current_dict[char]
                    current_dict = next_dict
                # 该关键字结束，状态转换为true
                if index == length - 1:
                    current_dict["is_end"] = True

        return state_event_dict


def dfs(keyword, after_list, pinyin_list, first_letter_list, cur_chars, w, length):
    if w == length:
        # 保存原形，为了能格式输出
        real_keyword[cur_chars] = keyword
        if cur_chars not in after_list:
            after_list.append(cur_chars)
        return
    dfs(keyword, after_list, pinyin_list, first_letter_list, cur_chars + first_letter_list[w], w + 1,
        length)
    dfs(keyword, after_list, pinyin_list, first_letter_list, cur_chars + pinyin_list[w], w + 1, length)
    # dfs(keyword, after_list, pianpang_list, pinyin_list, first_letter_list, cur_chars + pianpang_list[w], w + 1, length)


# 主要是为了能将关键词变形后填进关键词列表后返回
def word_handle(keyword_list):

    after_list = []
    for keyword in keyword_list:
        # 抛弃了汉字，全部转为拼音、英文单词
        if ord(keyword[0]) <= 255:
            after_list.append(keyword)
        real_keyword[keyword] = keyword
    # 扩充关键词列表
    for keyword in keyword_list:
        # 注意使用lazy_pinyin（一维列表）而不是pinyin（二维列表）
        if ord(keyword[0]) > 255:
            # 偏旁加入现有代码后回降低检测出其他敏感词的准确度，为了不捡芝麻丢西瓜，加上自身能力有限，只好放弃检测拆分汉字偏旁功能
            # pianpang_list = []
            # for index, hanzi in enumerate(keyword):
            #     temp = chaizi.get_chai(hanzi)
            #     temp2 = ""
            #     for j in temp:
            #         temp2 += j
            #         pianpangs.append(j)
            #     pianpang_list.append(temp2)
            # print(pianpang_list)
            pinyin_list = lazy_pinyin(keyword)
            # 首字母
            first_letter_list = lazy_pinyin(keyword, 4)
            # 判断是否中文避免数组越界（
            dfs(keyword, after_list, pinyin_list, first_letter_list, "", 0, len(keyword))
    return after_list


if __name__ == "__main__":
    dfa = DFA(word_handle(read_keywords(sys.argv[1])))
    ans = dfa.match(read_article(sys.argv[2]))
    write_ans(sys.argv[3], ans)

