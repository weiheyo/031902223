import copy
from pypinyin import lazy_pinyin
import sys
import cProfile
import chai

import pstats

# 存储变形后的敏感词的原形
real_keyword = {}


def read_keywords(file_path):
    with open(file_path, encoding='utf-8') as keyword_list:
        return keyword_list.read().splitlines()


def read_article(file_path):
    with open(file_path, encoding='utf-8') as article:
        return article.read()


def write_ans(file_path, ans_list):
    with open(file_path, 'w', encoding='utf-8') as ans:
        ans.write('total: '+str(ans_list[0])+'\n')
        for word in ans_list:
            if isinstance(word, int):
                continue
            # 按格式输出
            ans.write('line'+str(word['line'])+': '+'<'+real_keyword[word['keyword']]+'> ' + word['match'] + '\n')


class DFA:

    def __init__(self, keyword_list):
        self.state_event_dict = self._generate_state_event_dict(keyword_list)

    # 匹配
    def match(self, content: str):

        match_list = [0]
        state_list = []
        temp_match_list = []
        # 默认第一行
        which_line = 1
        for char in content:
            if char == '\n':
                which_line += 1

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
                    temp_match_list[index]["match"] += char
                    # 直接跳过字符到下一个
                    continue
                if char in state:
                    state_list[index] = state[char]
                    temp_match_list[index]["match"] += char
                    temp_match_list[index]["keyword"] += char

                    if state[char]["is_end"]:
                        match_list[0] += 1
                        match_list.append(copy.deepcopy(temp_match_list[index]))

                        if len(state[char].keys()) == 1:
                            state_list.pop(index)
                            temp_match_list.pop(index)
                else:
                    state_list.pop(index)
                    temp_match_list.pop(index)

        return match_list

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
        after_list.append(cur_chars)
        return
    dfs(keyword, after_list, pinyin_list, first_letter_list, cur_chars + first_letter_list[w], w + 1, length)
    dfs(keyword, after_list, pinyin_list, first_letter_list, cur_chars + pinyin_list[w], w + 1, length)


def word_handle(keyword_list):
    after_list = []

    # 小写
    for keyword in keyword_list:
        after_list.append(keyword.lower())
        real_keyword[keyword]=keyword
    # 转拼音
    for keyword in keyword_list:
        # 注意使用lazy_pinyin（一维列表）而不是pinyin（二维列表）
        # 使用了更高效率的方法
        # after_list.append("".join(lazy_pinyin(keyword)))
        pinyin_list = lazy_pinyin(keyword)
        # 首字母
        first_letter_list = lazy_pinyin(keyword, 4)
        # 判断是否中文避免数组越界（
        if ord(keyword[0]) > 255:
            dfs(keyword, after_list, pinyin_list, first_letter_list, "", 0, len(keyword))

    return after_list


if __name__ == "__main__":
    dfa = DFA(word_handle(read_keywords(sys.argv[1])))
    ans = dfa.match(read_article(sys.argv[2]))
    write_ans(sys.argv[3], ans)


    # 性能调试检测
    # p = pstats.Stats('result.out')
    # p.sort_stats('cumulative', 'name').print_stats(10)
    #
    # #
    # state_event_dict = {
    #     '你':{
    #         '真':{
    #             '帅':{
    #                 'is_end':True
    #             },'is_end':False
    #             '牛':{
    #                 'is_end':True
    #             },'is_end':False
    #         },
    #     },
    #     '我':{
    #         '真':{
    #             '好':{
    #                 'is_end':True
    #             },'is_end':False
    #         },'is_end':False
    #     }
    # },
    #
