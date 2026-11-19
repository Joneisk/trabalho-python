# 🎓 AVA: Ambiente Virtual de Aprendizagem na Oracle Cloud

Plataforma de ensino a distância em **Flask** com cursos, materiais, vídeos, fórum, quizzes e tarefas. Os arquivos de mídia ficam no **OCI Object Storage**.

## Funcionalidades
- Autenticação e perfis (aluno, professor e administrador)
- Gestão de cursos, matrículas e usuários
- Materiais, vídeos com acompanhamento de progresso (heartbeat) e conteúdo interativo
- **Fórum** por curso, avisos e notificações
- **Quizzes** e **tarefas** com correção e nota
- Biblioteca de e-books

## Stack
Python · Flask · Flask-SQLAlchemy · Flask-Login · Gunicorn · Oracle Cloud Infrastructure (Object Storage)

## Como rodar

```bash
pip install -r requirements.txt
# Configure as credenciais OCI via ~/.oci/config ou variáveis de ambiente (nunca no repositório)
python init_db.py
python run.py
```

A apresentação da arquitetura está em `apresentacao/`.
