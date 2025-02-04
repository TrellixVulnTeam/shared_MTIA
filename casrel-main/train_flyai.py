import time

import torch
import torch.nn.functional as F
from casrel import CasRel
from torch.utils.data import DataLoader
from dataloader import MyDataset, collate_fn
from tqdm import tqdm

device = 'cuda:0'
#device = 'cpu'
torch.set_num_threads(1)

def get_loss(pred, gold, mask):
    pred = pred.squeeze(-1)
    loss = F.binary_cross_entropy(pred, gold.float(), reduction='none') #以向量形式返回loss
    if loss.shape != mask.shape:
        mask = mask.unsqueeze(-1)
    loss = torch.sum(loss*mask)/torch.sum(mask)
    return loss

def evaluate():
    import os
    r = os.popen(
        'python3 ./test.py')
    result = r.read()
    print("test", result)
    r.close()

    r = os.popen(
        'python3 ./evaluate.py')
    result = r.read()
    print("f1", result)
    r.close()


if __name__ == '__main__':
    config = {'mode': 'train', 'batch_size': 16, 'epoch': 10, 'relation_types': 59, 'sub_weight': 1, 'obj_weight': 1}
    path = 'flyai_data/fixed_train.json'
    data = MyDataset(path, config)
    dataloader = DataLoader(data, batch_size=config['batch_size'], shuffle=True, collate_fn=collate_fn)
    model = CasRel(config).to(device)
    #torch.save(model.state_dict(), 'params.pkl')
    #model.load_state_dict(torch.load('params.pkl'))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-5, betas=(0.9, 0.999))
    loss_recorder = 0
    for epoch_index in range(config['epoch']):
        time_start = time.perf_counter()
        print('========= start training, epoch: {} ==========='.format(epoch_index))
        epoch_iterator = tqdm(iter(dataloader), desc="Iteration", position=0, leave=True, ncols=80)
        for batch_index, (sample, sub_start, sub_end, relation_start, relation_end, mask, sub_start_single, sub_end_single) in enumerate(epoch_iterator):
            batch_data = dict()
            batch_data['token_ids'] = sample
            batch_data['mask'] = mask
            batch_data['sub_start'] = sub_start_single
            batch_data['sub_end'] = sub_end_single
            pred_sub_start, pred_sub_end, pred_obj_start, pred_obj_end = model(batch_data)
            sub_start_loss = get_loss(pred_sub_start, sub_start, mask)
            sub_end_loss = get_loss(pred_sub_end, sub_end, mask)
            obj_start_loss = get_loss(pred_obj_start, relation_start, mask)
            obj_end_loss = get_loss(pred_obj_end, relation_end, mask)
            loss = config['sub_weight']*(sub_start_loss + sub_end_loss) + config['obj_weight']*(obj_start_loss + obj_end_loss)
            loss_recorder += loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            print("epoch: %d batch: %d loss: %f"% (epoch_index, batch_index, loss))
            if(batch_index%100 == 99):
                print(loss_recorder)
                loss_recorder = 0
        time_end = time.perf_counter()
        torch.save(model.state_dict(), 'params.pkl')
        print("successfully saved! time used = %fs."% (time_end-time_start))
        evaluate()