import os
import os.path as osp
from PIL import Image
import torch.utils.data as data
import torchvision.transforms as transforms

def is_image_file(filename):
    return any(filename.endswith(extension) for extension in [".png", ".jpg", ".jpeg"])

def default_loader(path):
    return Image.open(path).convert('RGB')


class DatasetImagelist(data.Dataset):
    def __init__(self, dataPath, imagelist, loadSize, fineSize, test=False, video=False):
        super(DatasetImagelist, self).__init__()
        self.dataPath = dataPath
        imagelist_from_dataPath = [x for x in os.listdir(dataPath) if is_image_file(x)]
        assert set(imagelist).issubset(imagelist_from_dataPath), 'imagelist not in datapath'
        self.image_list = sorted(imagelist)

        if(video):
            self.image_list = sorted(self.image_list)
        if not test:
            self.transform = transforms.Compose([
            		            transforms.Resize(fineSize),
            		            transforms.RandomCrop(fineSize),
                                    transforms.RandomHorizontalFlip(),
            		            transforms.ToTensor()])
        else:
            self.transform = transforms.Compose([
                                    transforms.Grayscale(num_output_channels=3),
                                    transforms.Resize(fineSize),
            		            transforms.ToTensor()])
        self.test = test

    def __getitem__(self,index):
        dataPath = os.path.join(self.dataPath,self.image_list[index])

        Img = default_loader(dataPath)
        ImgA = self.transform(Img)

        imgName = self.image_list[index]
        imgName = osp.splitext(imgName)[0]
        return ImgA,imgName

    def __len__(self):
        return len(self.image_list)

class Dataset(data.Dataset):
    def __init__(self, dataPath, loadSize, fineSize, test=False, video=False):
        super(Dataset,self).__init__()
        self.dataPath = dataPath
        self.image_list = [x for x in os.listdir(dataPath) if is_image_file(x)]
        self.image_list = sorted(self.image_list)
        if(video):
            self.image_list = sorted(self.image_list)
        if not test:
            self.transform = transforms.Compose([
                                    transforms.Resize(fineSize),
                                    transforms.RandomCrop(fineSize),
                                    transforms.RandomHorizontalFlip(),
                                    transforms.ToTensor()])
        else:
            self.transform = transforms.Compose([
                                    transforms.Resize(fineSize),
                                    transforms.ToTensor()])

        self.test = test

    def __getitem__(self,index):
        dataPath = os.path.join(self.dataPath,self.image_list[index])

        Img = default_loader(dataPath)
        ImgA = self.transform(Img)

        imgName = self.image_list[index]
        #imgName = imgName.split('.')[0]
        imgName = osp.splitext(imgName)[0]
        return ImgA,imgName

    def __len__(self):
        return len(self.image_list)

