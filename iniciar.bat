@echo off
echo Iniciando Sistema de Rotas de Entrega...
echo.

REM Verificar se .env existe
if not exist .env (
    echo ERRO: Arquivo .env nao encontrado!
    echo Por favor, copie .env.example para .env e configure suas credenciais
    echo.
    echo Execute: copy .env.example .env
    pause
    exit /b 1
)

REM Verificar se venv existe
if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
)

REM Ativar ambiente virtual
call venv\Scripts\activate

REM Instalar dependências
echo Instalando dependencias...
pip install -r requirements.txt

REM Criar pasta de uploads
if not exist uploads mkdir uploads

REM Iniciar aplicação
echo.
echo Iniciando aplicacao web...
echo Acesse: http://localhost:5000
echo.
python app.py

pause
