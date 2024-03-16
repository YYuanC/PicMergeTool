import streamlit as st
import io

# uploaded_file = st.file_uploader("Choose a file")

# if uploaded_file is not None:
#     file_contents = uploaded_file.getvalue()
#     # 将字节流转换为文件对象
#     file_obj = io.BytesIO(file_contents)
#     # 将文件保存到本地文件系统
#     with open(uploaded_file.name, "wb") as f:
#         f.write(file_contents)
#     # 获取文件路径
#     file_path = f.name
#     st.write(f"You selected '{uploaded_file.name}'")
#     st.write(f"File path: {file_path}")
#     st.write(uploaded_file)
from PIL import Image
import streamlit as st
# uploaded_files = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

# # if uploaded_file is not None:
# #     image = Image.open(uploaded_file)
# #     st.image(image, caption='Uploaded Image.', use_column_width=True)
# if(uploaded_files):
#     files = []
#     for uploaded_file in uploaded_files:
#         st.write("filename:", uploaded_file.name)
#         files.append(uploaded_file.read())
#         # with open(uploaded_file.name, "wb") as f:
#         #     f.write(uploaded_file.read())
#         image = Image.open(uploaded_file)
#         st.image(image, caption='Uploaded Image.', use_column_width=True)
st.text_input('Name', key='name')

def set_name(name):
    st.session_state.name = name
def set_upload(name):
    st.session_state.fileUploader1 = []


st.button('Clear name', on_click=set_name, args=[''])
st.button('Streamlit!', on_click=set_name, args=['Streamlit'])

uploaded_files = st.file_uploader("请选择图片：",type=['png', 'jpg', 'jpeg', "bmp", "ico", "tga", "tiff"], accept_multiple_files=True,help="支持的图片格式：png, jpg, jpeg, bmp, ico, tga, tiff",key="fileUploader1")#

st.button('Clear upload', on_click=set_upload, args=[''])

with st.form("my-form", clear_on_submit=True):
        file = st.file_uploader("upload file")
        submitted = st.form_submit_button("submit")