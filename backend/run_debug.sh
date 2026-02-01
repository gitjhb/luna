#!/bin/bash
cd /Users/hongbinj/clawd/projects/luna/backend
source venv/bin/activate
export MOCK_PAYMENT=false
export MOCK_DATABASE=false

# 启动服务器，设置特定logger的级别
python3 -c "
import logging
logging.getLogger('aiosqlite').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
" 

uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee -a server.log
