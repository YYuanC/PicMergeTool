# -*- coding: utf-8 -*-
import streamlit as st
import core
from io import BytesIO
import time
import pandas as pd
from PIL import Image
import base64

global direction,picNumOfDirection,TargetResolutionNum, outputPath , needTrim
def setParam(setdirection, setpicNumOfDirection):
    global direction,picNumOfDirection,TargetResolutionNum
    direction = setdirection
    picNumOfDirection = setpicNumOfDirection
    TargetResolutionNum = TargetResolution[1]

def bytes_to_base64_data_url(image_bytes, image_format="image/jpeg"):
  image = Image.open(BytesIO(image_bytes))
  buffered = BytesIO()
  image.save(buffered, format=image_format.split('/')[1])
  img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
  return f"data:{image_format};base64,{img_str}"

st.title("PicMerge")
tab1, tab2, tab3 = st.tabs(["基本", "调整" ,"分辨率/质量"])
with tab3:
    outputPath = st.text_input('输出目录', r'C:\output')
    st.write('生成的图片将会存放到', outputPath)
    option = st.selectbox(
            "图片分辨率",
            ("4K", "1080P"),
            index=0,
            placeholder="Please Select",
            )
    needTrim = st.checkbox("使用裁切为正方形",value=False)
    
    quality = st.slider('质量', 0, 100, 92)

    if(option == "1080P"):
        TargetResolution = [1920,1080]
    elif(option == "4K"):
        TargetResolution = [4096,2160]
    
with tab1:

    with st.form("my-form", clear_on_submit=True):
        uploaded_files = st.file_uploader("请选择图片：",type=['png', 'jpg', 'jpeg', "bmp", "ico", "tga", "tiff"], accept_multiple_files=True,key="fileUploader")
        needSort = st.checkbox("自动排序",value=False)
        submitted = st.form_submit_button("Upload")
    option = st.selectbox(
        "选择配置",
        ("竖直单列", "水平单列", "自定义"),
        index=0,
        placeholder="Please Select",
        )
    if(option == "水平单列"):
        setParam("水平排列", 1)
    if(option == "竖直单列"):
        setParam("竖直排列", 1)
    elif(option == "自定义"):
        direction = st.radio(
        "排列方式",["竖直排列", "水平排列" ],
        )
        if direction == '水平排列':
            picNumOfDirection = st.slider('排几行', 0, 9, 2)
            setParam(direction,picNumOfDirection)
            
        else:
            picNumOfDirection = st.slider('排几列', 0, 9, 2)
            setParam(direction,picNumOfDirection)

with tab2:
    enableAdvanced = st.toggle("自定义编辑",value=False)
    #if enableAdvanced:
    if uploaded_files:
        index = 1
        # 创建一个空的DataFrame，用于存放图片数据
        df = pd.DataFrame()
        for uploaded_file in uploaded_files:
            # 读取图片数据
            image_data = bytes_to_base64_data_url(uploaded_file.getvalue(), image_format=uploaded_file.type)
            # 添加图片到df
            temp_df = pd.DataFrame({'image': [image_data],'index': [index],"choose":True})
            df = pd.concat([df, temp_df], ignore_index=True)
            index += 1
        df = st.data_editor(df,
            column_config={
                "index": st.column_config.SelectboxColumn(
                    "Index",
                    help="Index of Image",
                    width="small",
                    options=range(1,index),
                    required=True,
                ),
                "image": st.column_config.ImageColumn(
                    "Image", help="Preview Image",width="small"
                )
            },hide_index=True,disabled= not enableAdvanced)
    else:
        pass


if uploaded_files:
    def doGenerate():
        progress_text = "处理中"
        progressBar = st.progress(0, text=progress_text)
        result = core.main(filesBytes,direction,picNumOfDirection,TargetResolutionNum, outputPath, quality, progressBar, needTrim)
        info = st.info(result)
        time.sleep(3)
        info.empty()
    if enableAdvanced :
        filesBytes = []
        if st.button("Generate"):
            # 按照index从小到大排序
            df = df.sort_values(by='index')
            for _, row in df.iterrows():
                if row["choose"]== True:
                    print(row["choose"])
                    # 提取图片数据
                    image_data = row["image"]
                    # 将base64编码的图片数据转换为字节流
                    image_bytes = base64.b64decode(image_data.split(',')[1])
                    # 将字节流添加到文件列表
                    filesBytes.append(BytesIO(image_bytes))
            doGenerate()
    else:
        if(needSort):
            uploaded_files = sorted(uploaded_files, key=lambda x: x.name)
        filesBytes = []
        for uploaded_file in uploaded_files:
            filesBytes.append(BytesIO(uploaded_file.getvalue()))
        doGenerate()
