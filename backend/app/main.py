# -*- coding: utf-8 -*-
"""
软件建设方案 AI 生成系统 - Flask 后端入口
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import config
from app.models.task import Base, GenerationTask, UploadedDocument, DocumentTemplate
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    CORS(app)
    
    app.config['SECRET_KEY'] = config.secret_key
    app.config['UPLOAD_FOLDER'] = config.upload_folder
    app.config['OUTPUT_FOLDER'] = config.output_folder
    app.config['MAX_CONTENT_LENGTH'] = config.max_file_size
    
    # 确保目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    # 初始化数据库
    init_database(app)
    
    # 注册路由
    register_routes(app)
    
    return app


def init_database(app):
    """初始化数据库"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'app.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    
    app.config['db_engine'] = engine
    app.config['db_session'] = sessionmaker(bind=engine)


def register_routes(app):
    """注册路由"""
    from app.api import documents, tasks, templates
    
    app.register_blueprint(documents.bp, url_prefix='/api/v1')
    app.register_blueprint(tasks.bp, url_prefix='/api/v1')
    app.register_blueprint(templates.bp, url_prefix='/api/v1')
    
    # 首页
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # 任务管理中心
    @app.route('/task-center')
    def task_center():
        return render_template('task_center.html')


# 创建应用实例
app = create_app()


if __name__ == '__main__':
    print("=" * 60)
    print("  软件建设方案 AI 生成系统 V2.0")
    print("=" * 60)
    print()
    print(f"  访问地址：http://localhost:5000")
    print(f"  API 文档：http://localhost:5000/docs")
    print()
    print("  按 Ctrl+C 停止服务")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
