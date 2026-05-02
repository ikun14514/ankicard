#!/usr/bin/env python3
"""
Anki Word Converter - Web Interface
Flask web application for converting documents to Anki flashcards
"""

import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile
import shutil
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

ALLOWED_EXTENSIONS = {'txt', 'docx'}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')


@app.route('/api/convert', methods=['POST'])
def convert_file():
    """处理文件转换请求"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式'}), 400

        output_format = request.form.get('output_format', 'csv')
        quiz_mode = request.form.get('quiz_mode', 'false').lower() == 'true'
        num_distractors = int(request.form.get('num_distractors', 3))
        use_ai = request.form.get('use_ai', 'true').lower() == 'true'
        api_key = request.form.get('api_key', '')
        base_url = request.form.get('base_url', '')

        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(filename).stem
        suffix = "_quiz" if quiz_mode else ""
        output_filename = f"{base_name}_anki{suffix}_{timestamp}.{output_format}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        from main import AnkiWordConverter

        converter = AnkiWordConverter()

        result = converter.run(
            input_file=input_path,
            output_file=output_path,
            api_key=api_key if api_key else None,
            base_url=base_url if base_url else None,
            output_format=output_format,
            preview_only=False,
            use_ai=use_ai,
            quiz_mode=quiz_mode,
            num_distractors=num_distractors,
            use_other_words_as_distractors=True
        )

        os.remove(input_path)

        if result['success']:
            download_url = f'/api/download/{output_filename}'
            return jsonify({
                'success': True,
                'cards_count': result['cards_count'],
                'output_file': result['output_file'],
                'download_url': download_url
            })
        else:
            error_msg = result.get('message', 'Unknown error')
            if result.get('errors'):
                error_msg = result['errors'][0]
            return jsonify({'error': error_msg}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>')
def download_file(filename):
    """下载生成的文件"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.teardown_appcontext
def cleanup(exception=None):
    """清理临时文件"""
    try:
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
    except:
        pass


if __name__ == '__main__':
    print("=" * 60)
    print("Anki单词转换器 - Web界面")
    print("=" * 60)
    print("启动服务器: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
