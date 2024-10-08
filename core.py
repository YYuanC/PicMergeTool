# -*- coding: utf-8 -*- 
# openWithRotateFromExif and merge module modified from xiaomingTang/img-handler
from typing import List, Tuple
from PIL import Image, ExifTags
from tangUtils.main import Base
import math, time, random, pathlib


Size = Tuple[int, int]
Box = Tuple[int, int, int, int]

def processPrinter(i: int, total: int, progressBar):
  i+=1
  if(i < total):
    progress_text = "处理中 " + str(i) + "/" + str(total)
    progressBar.progress(i/total, text=progress_text)
  elif(i >= total):
    progress_text = "已完成 "+ str(i) + "/" + str(total)
    progressBar.progress(1.0, text=progress_text)


def openWithRotateFromExif(file,needTrim):
  image = Image.open(file)
  try:
    for orientation in ExifTags.TAGS.keys():
      if ExifTags.TAGS[orientation] == 'Orientation':
        break

    exif = image._getexif()

    if exif[orientation] == 3:
      image = image.rotate(180, expand=True)
    elif exif[orientation] == 6:
      image = image.rotate(270, expand=True)
    elif exif[orientation] == 8:
      image = image.rotate(90, expand=True)
  except Exception as e:
    # cases: image don't have getexif
    pass
  try:
    if needTrim:  
      width, height = image.size
      min_dim = min(width, height)
      start_x = (width - min_dim) // 2
      start_y = (height - min_dim) // 2
      image = image.crop((start_x, start_y, start_x + min_dim, start_y + min_dim))
  except Exception as e:
    print("裁切时出错",e)
  return image

def geneJpg(size: Size):
  return Image.new("RGB", size, (255, 255, 255))

# Box: (left, upper, right, lower)
def paste(_from, _to, box: Box):
  toBeExtend = _to.size[0] < box[2] or _to.size[1] < box[3]
  if toBeExtend:
    newSize = (max(_to.size[0], box[2]), max(_to.size[1], box[3]))
    result = geneJpg(newSize)
    result.paste(_to, box=(0, 0))
    result.paste(_from, box=box)
    return result
  else:
    _to.paste(_from, box=box)
    return _to



# 文件名水平排列
def mergeHorizon(progressBar,needTrim, allFiles: List, rows: int = 1, height: int = 512):
  imgs = [openWithRotateFromExif(f,needTrim) for f in allFiles]
  total = len(imgs)
  cols = math.ceil(total / rows)
  base = geneJpg((1, 1))
  corner = [0, 0]
  for row in range(rows):
    corner[0] = 0
    corner[1] = height * row
    for col in range(cols):
      i = row * cols + col
      processPrinter(i, total,progressBar)
      if i >= total:
        return base
      im = imgs[i]
      w, h = im.size
      newSize = (math.ceil(w * height / h), height)
      resizedIm = im.resize(newSize, Image.LANCZOS)
      newBox = (corner[0], corner[1], corner[0] + newSize[0], corner[1] + newSize[1])
      base = paste(resizedIm, base, newBox)
      corner[0] += newSize[0]
  return base

# 文件名竖直排列
def mergeVertical(progressBar, needTrim, allFiles: List[str], cols: int = 1, width: int = 512):
  imgs = [openWithRotateFromExif(f,needTrim) for f in allFiles]
  total = len(imgs)
  rows = math.ceil(total / cols)
  base = geneJpg((1, 1))
  corner = [0, 0]
  for col in range(cols):
    corner[0] = width * col
    corner[1] = 0
    for row in range(rows):
      i = col * rows + row
      processPrinter(i, total, progressBar)
      if i >= total:
        return base
      im = imgs[i]
      w, h = im.size
      newSize = (width, math.ceil(h * width / w))
      resizedIm = im.resize(newSize, Image.LANCZOS)
      newBox = (corner[0], corner[1], corner[0] + newSize[0], corner[1] + newSize[1])
      base = paste(resizedIm, base, newBox)
      corner[1] += newSize[1]
  return base

def main(allFiles,direction,picNumOfDirection,TargetResolutionNum,outputPath, quality, progressBar,needTrim):
  
  try:
    resultName = "图片拼接--%s--%s" % (time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()), random.randint(1, 10000))
    result = Base(outputPath).childOf("%s.jpg" % resultName)
    result.parent.createAsDir()
    if(direction == "水平排列"):
      mergeHorizon(
        progressBar,
        needTrim,
        allFiles,
        picNumOfDirection,
        TargetResolutionNum
      ).save(result.path, optimize=True, quality=quality, progressive=True, subsampling=1)
    else:
      mergeVertical(
        progressBar,
        needTrim,
        allFiles,
        picNumOfDirection,
        TargetResolutionNum
      ).save(result.path, optimize=True, quality=quality, progressive=True, subsampling=1)

    return "图片已保存到 【%s】" % result.path
  except Exception as e:
    print("【图片生成失败】", e)
    try:
      pathlib.Path.unlink(result.path)
      return "【生成的无效图片已被删除】%s" % result.path
    except Exception as e:
      return "【生成的无效图片删除失败, 请手动删除】%s" % result.path


