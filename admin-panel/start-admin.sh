 #!/bin/bash

# Luna Admin Panel 启动脚本

echo "🌙 Luna Admin Panel 启动脚本"
echo "================================"

# 检查 Luna 后端是否运行
echo "📡 检查后端状态..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Luna 后端正在运行"
else
    echo "❌ Luna 后端未运行，正在启动..."
    cd /Users/hongbinj/clawd/projects/luna/backend
    
    # 杀死可能存在的进程
    pkill -9 -f "uvicorn" 2>/dev/null
    sleep 2
    
    # 启动后端
    source venv/bin/activate
    export MOCK_PAYMENT=false
    export MOCK_DATABASE=false
    export ALLOW_GUEST=true
    
    echo "⚡ 启动 Luna 后端服务..."
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
    
    # 等待启动
    echo "⏳ 等待服务启动..."
    for i in {1..10}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ 后端启动成功"
            break
        fi
        sleep 1
    done
    
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "❌ 后端启动失败，请检查日志"
        exit 1
    fi
fi

# 检查端口8080是否被占用
if lsof -i:8080 > /dev/null 2>&1; then
    echo "⚠️  端口 8080 已被占用，将使用端口 8081"
    PORT=8081
else
    PORT=8080
fi

# 启动 HTTP 服务器
cd /Users/hongbinj/clawd/projects/luna/admin-panel
echo "🚀 启动 Admin Panel HTTP 服务器..."
echo "📍 访问地址: http://localhost:${PORT}"
echo ""
echo "🎯 功能说明:"
echo "   📊 概览 - 系统统计和用户活跃度"
echo "   💬 聊天记录 - 用户对话历史查看"
echo "   ⏰ 主动消息 - 测试主动消息发送"
echo "   📝 角色管理 - 查看和管理角色"
echo "   💝 亲密度 - 用户关系数据统计"
echo ""
echo "📝 使用说明: 查看 README.md"
echo "🛑 停止服务: 按 Ctrl+C"
echo ""
echo "正在启动服务器..."

# 启动 HTTP 服务器
python3 -m http.server ${PORT}
