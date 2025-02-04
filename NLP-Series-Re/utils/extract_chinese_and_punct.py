#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2019 Baidu.com, Inc. All Rights Reserved
#
"""
requirements:
Authors: daisongtai(daisongtai@baidu.com)
Date:    2019/5/29 6:38 PM
"""
from __future__ import print_function

import re

from transformers import BertTokenizer


max_seq_length = 500
# tokenizer = BertTokenizer.from_pretrained('transformer_cpt/bert', do_lower_case=True)
tokenizer = BertTokenizer.from_pretrained('/kaggle/working', do_lower_case=True)

LHan = [
    [0x2E80, 0x2E99],  # Han # So  [26] CJK RADICAL REPEAT, CJK RADICAL RAP
    [0x2E9B, 0x2EF3
     ],  # Han # So  [89] CJK RADICAL CHOKE, CJK RADICAL C-SIMPLIFIED TURTLE
    [0x2F00, 0x2FD5],  # Han # So [214] KANGXI RADICAL ONE, KANGXI RADICAL FLUTE
    0x3005,  # Han # Lm       IDEOGRAPHIC ITERATION MARK
    0x3007,  # Han # Nl       IDEOGRAPHIC NUMBER ZERO
    [0x3021,
     0x3029],  # Han # Nl   [9] HANGZHOU NUMERAL ONE, HANGZHOU NUMERAL NINE
    [0x3038,
     0x303A],  # Han # Nl   [3] HANGZHOU NUMERAL TEN, HANGZHOU NUMERAL THIRTY
    0x303B,  # Han # Lm       VERTICAL IDEOGRAPHIC ITERATION MARK
    [
        0x3400, 0x4DB5
    ],  # Han # Lo [6582] CJK UNIFIED IDEOGRAPH-3400, CJK UNIFIED IDEOGRAPH-4DB5
    [
        0x4E00, 0x9FC3
    ],  # Han # Lo [20932] CJK UNIFIED IDEOGRAPH-4E00, CJK UNIFIED IDEOGRAPH-9FC3
    [
        0xF900, 0xFA2D
    ],  # Han # Lo [302] CJK COMPATIBILITY IDEOGRAPH-F900, CJK COMPATIBILITY IDEOGRAPH-FA2D
    [
        0xFA30, 0xFA6A
    ],  # Han # Lo  [59] CJK COMPATIBILITY IDEOGRAPH-FA30, CJK COMPATIBILITY IDEOGRAPH-FA6A
    [
        0xFA70, 0xFAD9
    ],  # Han # Lo [106] CJK COMPATIBILITY IDEOGRAPH-FA70, CJK COMPATIBILITY IDEOGRAPH-FAD9
    [
        0x20000, 0x2A6D6
    ],  # Han # Lo [42711] CJK UNIFIED IDEOGRAPH-20000, CJK UNIFIED IDEOGRAPH-2A6D6
    [0x2F800, 0x2FA1D]
]  # Han # Lo [542] CJK COMPATIBILITY IDEOGRAPH-2F800, CJK COMPATIBILITY IDEOGRAPH-2FA1D

CN_PUNCTS = [(0x3002, "。"), (0xFF1F, "？"), (0xFF01, "！"), (0xFF0C, "，"),
             (0x3001, "、"), (0xFF1B, "；"), (0xFF1A, "："), (0x300C, "「"),
             (0x300D, "」"), (0x300E, "『"), (0x300F, "』"), (0x2018, "‘"),
             (0x2019, "’"), (0x201C, "“"), (0x201D, "”"), (0xFF08, "（"),
             (0xFF09, "）"), (0x3014, "〔"), (0x3015, "〕"), (0x3010, "【"),
             (0x3011, "】"), (0x2014, "—"), (0x2026, "…"), (0x2013, "–"),
             (0xFF0E, "．"), (0x300A, "《"), (0x300B, "》"), (0x3008, "〈"),
             (0x2460, "①"), (0x2461, "②"), (0x2462, "③"), (0x2463, "④"),
             (0x2464, "⑤"), (0x2465, "⑥"), (0x2466, "⑦"), (0x2467, "⑧"), (0x2468, "⑨"), (0x2469, "⑩"),
             (0x3009, "〉"), (0x2015, "―"), (0xff0d, "－"), (0x0020, " "), (0xFF5E, "～")]
# (0xFF5E, "～"),

EN_PUNCTS = [[0x0021, 0x002F], [0x003A, 0x0040], [0x005B, 0x0060],
             [0x007B, 0x007E]]


class ChineseAndPunctuationExtractor(object):
    def __init__(self):
        self.chinese_re = self.build_re()

    def is_chinese_or_punct(self, c):
        if self.chinese_re.match(c):
            return True
        else:
            return False

    def build_re(self):
        L = []
        for i in LHan:
            if isinstance(i, list):
                f, t = i
                try:
                    f = chr(f)
                    t = chr(t)
                    L.append('%s-%s' % (f, t))
                except:
                    pass  # A narrow python build, so can't use chars > 65535 without surrogate pairs!

            else:
                try:
                    L.append(chr(i))
                except:
                    pass
        for j, _ in CN_PUNCTS:
            try:
                L.append(chr(j))
            except:
                pass

        for k in EN_PUNCTS:
            f, t = k
            try:
                f = chr(f)
                t = chr(t)
                L.append('%s-%s' % (f, t))
            except:
                raise ValueError()
                pass  # A narrow python build, so can't use chars > 65535 without surrogate pairs!

        RE = '[%s]' % ''.join(L)
        # print('RE:', RE.encode('utf-8'))
        return re.compile(RE, re.UNICODE)


if __name__ == '__main__':
    extractor = ChineseAndPunctuationExtractor()
    # for c in "韩邦庆（1856～1894）曾用名寄，字子云，别署太仙、大一山人、花也怜侬、三庆":
    #     if extractor.is_chinese_or_punct(c):
    #         print(c, 'yes')
    #     else:
    #         print(c, "no")
    #
    # print("～", extractor.is_chinese_or_punct("～"))
    # print("~", extractor.is_chinese_or_punct("~"))
    # print("―", extractor.is_chinese_or_punct("―"))
    # print("-", extractor.is_chinese_or_punct("-"))

    text_raw = "（3）抗甲状腺球蛋白及抗甲状腺微粒体抗体（TGA与TPO）：在桥本甲状腺炎患者血清中高滴度TGA90%～95%，TPO检测也有相应诊断价值"

    sub_text = []
    buff = ""
    flag_en = False
    flag_digit = False
    for char in text_raw:
        if extractor.is_chinese_or_punct(char):
            if buff != "":
                sub_text.append(buff)
                buff = ""
            sub_text.append(char)
            flag_en = False
            flag_digit = False
        else:
            if re.compile('\d').match(char):
                if buff != "" and flag_en:
                    sub_text.append(buff)
                    buff = ""
                    flag_en = False
                flag_digit = True
                buff += char
            else:
                if buff != "" and flag_digit:
                    sub_text.append(buff)
                    buff = ""
                    flag_digit = False
                flag_en = True
                buff += char

    if buff != "":
        sub_text.append(buff)

    tok_to_orig_start_index = []
    tok_to_orig_end_index = []
    tokens = []
    text_tmp = ''
    for (i, token) in enumerate(sub_text):
        sub_tokens = tokenizer.tokenize(token) if token != ' ' else []
        text_tmp += token
        for sub_token in sub_tokens:
            tok_to_orig_start_index.append(len(text_tmp) - len(token))
            tok_to_orig_end_index.append(len(text_tmp) - 1)
            tokens.append(sub_token)
            if len(tokens) >= max_seq_length - 2:
                break
        else:
            continue
        break

    print(sub_text)
    print(tokens)
