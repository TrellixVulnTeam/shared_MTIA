# _*_ coding:utf-8 _*_
import warnings

import numpy as np
import torch
import torch.nn as nn
from transformers import BertModel
from transformers import BertPreTrainedModel

from .layernorm import ConditionalLayerNorm
#from utils.data_util import batch_gather

warnings.filterwarnings("ignore")

def batch_gather(data: torch.Tensor, index: torch.Tensor):
    length = index.shape[0]
    t_index = index.cpu().numpy()
    t_data = data.cpu().data.numpy()
    result = []
    for i in range(length):
        result.append(t_data[i, t_index[i], :])

    return torch.from_numpy(np.array(result)).to(data.device)

class ERENet(nn.Module):
    """
    ERENet : entity relation jointed extraction
    """

    def __init__(self, encoder, classes_num):
        super().__init__()
        self.classes_num = classes_num

        # BERT model
        self.bert = encoder
        config = encoder.config

        self.token_entity_emb = nn.Embedding(num_embeddings=2, embedding_dim=config.hidden_size,
                                             padding_idx=0)
        # self.encoder_layer = TransformerEncoderLayer(config.hidden_size, nhead=4)
        # self.transformer_encoder = TransformerEncoder(self.encoder_layer, num_layers=1)
        self.LayerNorm = ConditionalLayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        # pointer net work
        self.po_dense = nn.Linear(config.hidden_size, self.classes_num * 2)
        self.subject_dense = nn.Linear(config.hidden_size, 2)
        self.loss_fct = nn.BCEWithLogitsLoss(reduction='none')

        #self.init_weights()

    def forward(self, q_ids=None, passage_ids=None, segment_ids=None, attention_mask=None, subject_ids=None,
                subject_labels=None,
                object_labels=None, eval_file=None,
                is_eval=False):
        mask = (passage_ids != 0).float()
        bert_encoder = self.bert(passage_ids, token_type_ids=segment_ids, attention_mask=mask)[0]
        if not is_eval:
            # subject_encoder = self.token_entity_emb(token_type_ids)
            # context_encoder = bert_encoder + subject_encoder

            sub_start_encoder = batch_gather(bert_encoder, subject_ids[:, 0])
            sub_end_encoder = batch_gather(bert_encoder, subject_ids[:, 1])
            subject = torch.cat([sub_start_encoder, sub_end_encoder], 1)
            context_encoder = self.LayerNorm(bert_encoder, subject)

            sub_preds = self.subject_dense(bert_encoder)
            po_preds = self.po_dense(context_encoder).reshape(passage_ids.size(0), -1, self.classes_num, 2)

            subject_loss = self.loss_fct(sub_preds, subject_labels)
            # subject_loss = F.binary_cross_entropy(F.sigmoid(sub_preds) ** 2, subject_labels, reduction='none')
            subject_loss = subject_loss.mean(2)
            subject_loss = torch.sum(subject_loss * mask.float()) / torch.sum(mask.float())

            po_loss = self.loss_fct(po_preds, object_labels)
            # po_loss = F.binary_cross_entropy(F.sigmoid(po_preds) ** 4, object_labels, reduction='none')
            po_loss = torch.sum(po_loss.mean(3), 2)
            po_loss = torch.sum(po_loss * mask.float()) / torch.sum(mask.float())

            loss = subject_loss + po_loss

            return loss

        else:

            subject_preds = nn.Sigmoid()(self.subject_dense(bert_encoder))
            answer_list = list()
            for qid, sub_pred in zip(q_ids.cpu().numpy(),
                                     subject_preds.cpu().numpy()):
                context = eval_file[qid].bert_tokens
                start = np.where(sub_pred[:, 0] > 0.6)[0]
                end = np.where(sub_pred[:, 1] > 0.5)[0]
                subjects = []
                for i in start:
                    j = end[end >= i]
                    if i == 0 or i > len(context) - 2:
                        continue

                    if len(j) > 0:
                        j = j[0]
                        if j > len(context) - 2:
                            continue
                        subjects.append((i, j))

                answer_list.append(subjects)

            qid_ids, bert_encoders, pass_ids, subject_ids, token_type_ids = [], [], [], [], []
            for i, subjects in enumerate(answer_list):
                if subjects:
                    qid = q_ids[i].unsqueeze(0).expand(len(subjects))
                    pass_tensor = passage_ids[i, :].unsqueeze(0).expand(len(subjects), passage_ids.size(1))
                    new_bert_encoder = bert_encoder[i, :, :].unsqueeze(0).expand(len(subjects), bert_encoder.size(1),
                                                                                 bert_encoder.size(2))

                    token_type_id = torch.zeros((len(subjects), passage_ids.size(1)), dtype=torch.long)
                    for index, (start, end) in enumerate(subjects):
                        token_type_id[index, start:end + 1] = 1

                    qid_ids.append(qid)
                    pass_ids.append(pass_tensor)
                    subject_ids.append(torch.tensor(subjects, dtype=torch.long))
                    bert_encoders.append(new_bert_encoder)
                    token_type_ids.append(token_type_id)

            if len(qid_ids) == 0:
                subject_ids = torch.zeros(1, 2).long().to(bert_encoder.device)
                qid_tensor = torch.tensor([-1], dtype=torch.long).to(bert_encoder.device)
                po_tensor = torch.zeros(1, bert_encoder.size(1)).long().to(bert_encoder.device)
                return qid_tensor, subject_ids, po_tensor

            qids = torch.cat(qid_ids).to(bert_encoder.device)
            pass_ids = torch.cat(pass_ids).to(bert_encoder.device)
            bert_encoders = torch.cat(bert_encoders).to(bert_encoder.device)
            # token_type_ids = torch.cat(token_type_ids).to(bert_encoder.device)
            subject_ids = torch.cat(subject_ids).to(bert_encoder.device)

            flag = False
            split_heads = 1024

            bert_encoders_ = torch.split(bert_encoders, split_heads, dim=0)
            pass_ids_ = torch.split(pass_ids, split_heads, dim=0)
            # token_type_ids_ = torch.split(token_type_ids, split_heads, dim=0)
            subject_encoder_ = torch.split(subject_ids, split_heads, dim=0)

            po_preds = list()
            for i in range(len(bert_encoders_)):
                bert_encoders = bert_encoders_[i]
                # token_type_ids = token_type_ids_[i]
                pass_ids = pass_ids_[i]
                subject_encoder = subject_encoder_[i]

                if bert_encoders.size(0) == 1:
                    flag = True
                    # print('flag = True**********')
                    bert_encoders = bert_encoders.expand(2, bert_encoders.size(1), bert_encoders.size(2))
                    subject_encoder = subject_encoder.expand(2, subject_encoder.size(1))
                    # pass_ids = pass_ids.expand(2, pass_ids.size(1))

                sub_start_encoder = batch_gather(bert_encoders, subject_encoder[:, 0])
                sub_end_encoder = batch_gather(bert_encoders, subject_encoder[:, 1])
                subject = torch.cat([sub_start_encoder, sub_end_encoder], 1)
                context_encoder = self.LayerNorm(bert_encoders, subject)

                po_pred = self.po_dense(context_encoder).reshape(subject_encoder.size(0), -1, self.classes_num, 2)

                if flag:
                    po_pred = po_pred[1, :, :, :].unsqueeze(0)

                po_preds.append(po_pred)

            po_tensor = torch.cat(po_preds).to(qids.device)
            po_tensor = nn.Sigmoid()(po_tensor)
            return qids, subject_ids, po_tensor
