# -*- coding: utf-8 -*-
"""
@Time : 2020/12/1110:44
@Auth : 周俊贤
@File ：run.py
@DESCRIPTION:

"""
import json
import os
import time

import torch
from torch.utils.data import DataLoader
from transformers import BertTokenizerFast

from dataset.dataset import DuIEDataset
from dataset.dataset import collate_fn
from models.model import DuIE_model
from run import evaluate
from utils.finetuning_argparse import get_argparse
from utils.utils import seed_everything, init_logger, logger


def main():
    parser = get_argparse()
    parser.add_argument("--fine_tunning_model",
                        type=str,
                        required=True,
                        help="fine_tuning model path")
    args = parser.parse_args()
    print(json.dumps(vars(args), sort_keys=True, indent=4, separators=(', ', ': '), ensure_ascii=False))
    init_logger(log_file="./log/{}.log".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
    seed_everything(args.seed)

    # 设置保存目录
    if not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)

    # Reads label_map.
    '''
    with open("./data/predicate2id.json", 'r', encoding='utf8') as fp:
        label_map = json.load(fp)
    num_classes = (len(label_map.keys()) - 2) * 2 + 2
    '''
    id2predicate, predicate2id, n = {0: "O", 1: "I"}, {"O": 0, "I": 1}, 2
    with open('emergency_data/train/schema.csv') as f:
        predicate2type = {}
        line_count = 0
        for l in f:
            if line_count == 0:
                line_count += 1
                continue
            line = l.strip()
            if line != 'null':
                items = line.split(',')
                predicate_type = items[0]+"_"+items[1]+"_"+items[2]
                subject_type = items[0]
                object_type = items[2]
                predicate2type[predicate_type] = (subject_type, object_type)
                key = predicate_type
                id2predicate[n] = key
                predicate2id[key] = n
                n += 1
            line_count += 1
    label_map = predicate2id
    num_classes = (len(label_map.keys()) - 2) * 2 + 2

    # device
    args.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    # tokenizer
    tokenizer = BertTokenizerFast.from_pretrained('/opt/kelvin/python/knowledge_graph/ai_contest/input/bert-roberta')
    args.cls_token_id = tokenizer.cls_token_id
    args.sep_token_id = tokenizer.sep_token_id
    args.pad_token_id = tokenizer.pad_token_id

    # Dataset & Dataloader
    test_dataset = DuIEDataset(args,
                               json_path="emergency_data/train/unlabeled.json",
                               tokenizer=tokenizer)

    test_iter = DataLoader(test_dataset,
                           shuffle=False,
                           batch_size=args.per_gpu_eval_batch_size,
                           collate_fn=collate_fn,
                           num_workers=0)
    logger.info("The nums of the train_dataset features is {}".format(len(test_dataset)))
    logger.info("The nums of the eval_dataset features is {}".format(len(test_dataset)))

    # model
    model = DuIE_model(args.model_name_or_path, num_classes=num_classes).to(args.device)
    model.load_state_dict(torch.load(args.fine_tunning_model))

    # 训练
    model.eval()
    evaluate(args, test_iter, model, mode="test", id2predicate=id2predicate)


if __name__ == "__main__":
    main()
