import os
from os import listdir
from os.path import isfile, join
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import numpy as np

current_dir = os.path.dirname(os.path.realpath(__file__))
img_dir = os.path.join(current_dir, 'images/0x5/png')
imgs = [i for i in listdir(img_dir) if i.endswith('.png')]

modified_imgs = []
for img_file in imgs:
    year_str = img_file.split('.png')[0]
    img = Image.open(os.path.join(img_dir, img_file))
    draw = ImageDraw.Draw(img)
    # font = ImageFont.truetype(<font-file>, <font-size>)
    font = ImageFont.truetype("arial.ttf", 22)
    # draw.text((x, y),"Sample Text",(r,g,b))
    draw.text((15, 15), year_str, (255, 255, 255), font=font)
    # img.save('sample-out.png')
    modified_imgs.append(img)

#ensure images all have same size
min_shape = sorted([(np.sum(i.size), i.size ) for i in modified_imgs])[0][1]

# total of 24 images, arranged as 4x6
modified_imgs = np.array(modified_imgs, dtype=object)
modified_imgs = np.reshape(modified_imgs, (-1, 6))

vstack_list = []
for hstack_list in modified_imgs:
    vstack_list.append(np.hstack((np.asarray(i.resize(min_shape)) for i in hstack_list)))
imgs_comb = np.vstack((np.asarray(i) for i in vstack_list))

imgs_comb = Image.fromarray(imgs_comb)
imgs_comb.save('1997-2020_votes.png')
