import streamlit as st
# To make things easier later, we're also importing numpy and pandas for
# working with sample data.
import numpy
import pandas

st.title("图片拼接工具")
 
uploaded_file = st.file_uploader("请选择图片：",type=['png', 'jpg', 'jpeg'], accept_multiple_files=True,help="type=png,jpg,jpeg]")#
if uploaded_file is not None:
    # To read file as bytes:
    bytes_data = uploaded_file.getvalue()
    st.write(bytes_data)
    print(111)



disable=False

cb = st.checkbox('使用预设',value=True)
 
if cb:
    disable=True
    
    st.write('确认成功')
else:
    disable=False
    st.write('没有确认')
age = st.slider('How old are you?', 0, 9, 2, disabled=disable)
st.write("I'm ", age, 'years old')