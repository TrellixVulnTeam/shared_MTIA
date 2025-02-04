import json
import numpy as np
from tqdm import tqdm
import extract_convert_bdci as convert
import extract_vectorize_bdci as vectorize
import extract_model_bdci as extract
from bert4keras.snippets import text_segmentate
from snippets import *

def text_split_test(text, limited=True):
    """将长句按照标点分割为多个子句。
    """
    #texts = text_segmentate(text, 1, u'\n。；：，')
    texts = text_segmentate(text, 1, u'\n')
    if limited:
        texts = texts[-convert.maxlen:]
    return texts

def load_test_data(filename):
    """加载数据
    返回：[(text, summary)]
    """
    D = []
    with open(filename, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i == 0:
                continue
            parts = line.strip().split('|')
            id_ = parts[0]
            content = parts[1]
            abstract = ""
            D.append((content, abstract))
    return D


def predict(text, labels):
    # 抽取
    texts = text_split_test(text)
    vecs = vectorize.predict(texts)
    extract.model.load_weights('weights/extract_model.%s.weights' %  0)
    preds = extract.model.predict(vecs[None])[0, :, 0]
    sent_num = 0
    #print('=== pred_num: {}, label_num: {}'.format(len(preds), len(labels)))
    for pred in preds:
    	label = 0
    	if sent_num in labels:
    		label = 1
    	#print('sent_num {}, pred {}, label {}'.format(sent_num, pred, label))
    	sent_num += 1
    preds = np.where(preds > extract.threshold)[0]
    summary = ''.join([texts[i] for i in preds])
    return summary

'''
if __name__ == '__main__':

    from tqdm import tqdm

    data = extract.load_data(extract.data_extract_json)
    valid_data = data #data_split(data, fold, num_folds, 'valid')
    total_metrics = {k: 0.0 for k in metric_keys}
    results = []
    for d in tqdm(valid_data, desc=u'转换中'):
        text = '\n'.join(d[0])
        pred_summary = predict(text, d[1])
        label_summary = ''.join([d[0][i] for i in d[1]])
        #print(summary)
        metrics = compute_metrics(pred_summary, d[2])
        for k, v in metrics.items():
            total_metrics[k] += v
        result = {
            'source_1': pred_summary,
            'source_2': label_summary,
            'target': d[2],
        }
        results.append(result)

    F = open('bdci_datasets/fixed_train_dataset.json', 'w', encoding='utf-8')
    for d in results:
        F.write(json.dumps(d, ensure_ascii=False) + '\n')

    metrics = {k: v / len(valid_data) for k, v in total_metrics.items()}
    print(metrics)
'''

if __name__ == '__main__':
	data = load_test_data('./bdci_datasets/test_dataset.csv')
	results = []
	for d in tqdm(data, desc=u'转换中'):
		text = d[0]
		pred_summary = predict(text, [])
		result = {
			'source_1': pred_summary,
			'source_2': "",
			'target': "",
		}
		results.append(result)

	F = open('bdci_datasets/fixed_test_dataset.json', 'w', encoding='utf-8')
	for d in results:
		F.write(json.dumps(d, ensure_ascii=False) + '\n')

