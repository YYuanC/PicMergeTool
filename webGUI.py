# -*- coding: utf-8 -*-
import streamlit as st
# To make things easier later, we're also importing numpy and pandas for
# working with sample data.
import numpy
import pandas
import core
st.title("PicMerge")
from io import BytesIO
import time


global direction,picNumOfDirection,TargetResolutionNum, outputPath , needTrim
def setParam(setdirection, setpicNumOfDirection):
    global direction,picNumOfDirection,TargetResolutionNum
    direction = setdirection
    picNumOfDirection = setpicNumOfDirection
    TargetResolutionNum = TargetResolution[1]




tab1, tab2 = st.tabs(["基本", "分辨率/质量"])
with tab2:
    outputPath = st.text_input('输出目录', r'C:\Users\Public\Apps\拼图工具\output')
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
        submitted = st.form_submit_button("Generate")
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

        
    if uploaded_files:
        if(needSort):
            uploaded_files = sorted(uploaded_files, key=lambda x: x.name)
        filesBytes = []
        for uploaded_file in uploaded_files:
            #st.write("filename:", uploaded_file.name)
            filesBytes.append(BytesIO(uploaded_file.getvalue()))
        progress_text = "处理中"
        progressBar = st.progress(0, text=progress_text)
        result = core.main(filesBytes,direction,picNumOfDirection,TargetResolutionNum, outputPath, quality, progressBar, needTrim)

        info = st.info(result)
        time.sleep(3)
        info.empty()