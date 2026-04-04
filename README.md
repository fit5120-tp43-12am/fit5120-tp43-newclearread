# 团队开发说明

# 项目结构说明

project-root/
│
├── frontend/ # 前端（Vue 3 + Vite）
├── backend/ # 后端（FastAPI）
├── database/ # （暂未使用）数据库脚本
├── docs/ # （可选）文档
├── docker/ # （后期）部署


#  后端结构（FastAPI）
backend/
│
├── main.py # 项目入口（启动 FastAPI）
├── config.py # 配置文件
│
├── core/ # 核心配置（数据库等）
│ └── database.py
│
├── routes/ # 写 API 接口
│ └── api.py
│
├── services/ # 写业务逻辑（最重要）
│
├── models/ # 数据模型（数据库结构）
│
├── repositories/ # 数据库操作
│
├── utils/ # 工具函数
│
└── venv/ # 虚拟环境（不要提交到git）已经在 .gitignore里设置好了


简单理解：

- routes = 对外接口
- services = 真正干活的地方（核心）
- models = 数据长什么样
- repositories = 数据库读写


#  前端结构（Vue）
frontend/
│
├── src/
│ ├── pages/ # 页面
│ ├── components/ # 组件
│ ├── services/ # 调后端 API
│ ├── router/ # 路由
│ ├── assets/ # 图片等
│ ├── App.vue # 根组件
│ └── main.js # 入口
│
├── public/
├── node_modules/ #不要提交到git（已经在 .gitignore里设置好了）
└── vite.config.js


---

#  前后端关系

- 前端运行：`http://localhost:5173`
- 后端运行：`http://127.0.0.1:8000`

前端调用后端 API，例如：
http://127.0.0.1:8000/api/test



# 如何运行项目


## 后端启动

```bash
cd backend

# 第一次需要创建
python -m venv venv

# 激活（Windows）
venv\Scripts\activate

# 安装依赖
pip install fastapi uvicorn

# 启动
uvicorn main:app --reload

# 打开测试：

http://127.0.0.1:8000/docs


前端启动
cd frontend

npm install
npm run dev

 打开：

http://localhost:5173