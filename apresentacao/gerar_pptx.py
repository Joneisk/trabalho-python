from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

def create_presentation():
    prs = Presentation()

    def add_slide(title_text, content_items=None, is_image_slide=False):
        slide_layout = prs.slide_layouts[1] # Title and Content
        slide = prs.slides.add_slide(slide_layout)
        title = slide.shapes.title
        title.text = title_text
        
        if content_items:
            tf = slide.placeholders[1].text_frame
            for item in content_items:
                p = tf.add_paragraph()
                p.text = item
                p.level = 0

        if is_image_slide:
            # Create a placeholder box for image
            left = Inches(1)
            top = Inches(2.5)
            width = Inches(8)
            height = Inches(4)
            shape = slide.shapes.add_textbox(left, top, width, height)
            fill = shape.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(230, 230, 230)
            text_frame = shape.text_frame
            p = text_frame.add_paragraph()
            p.text = "[ANEXAR DIAGRAMA/IMAGEM AQUI]"
            p.alignment = PP_ALIGN.CENTER
            text_frame.vertical_anchor = 1 # Middle

    # Slide 1: Title
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "Arquitetura de Nuvem: Sistema AVA"
    subtitle.text = "Design de Infraestrutura em Oracle Cloud (OCI)\nFoco em Escalabilidade e Colaboração"

    # Slide 2: Introdução
    add_slide("Visão Geral da Solução", [
        "Plataforma completa de Ambiente Virtual de Aprendizagem (AVA).",
        "Suporte a Vídeo-aulas (Streaming) e Chat em tempo real.",
        "Gestão de Atividades, Quizzes e Biblioteca Digital.",
        "Foco em alta disponibilidade e performance."
    ])

    # Slide 3: Especificações Técnicas (VM)
    add_slide("Infraestrutura: Computação", [
        "Provedor: Oracle Cloud Infrastructure (OCI).",
        "Forma (Shape): VM.Standard3.Flex (Intel Ice Lake).",
        "Sistema Operacional: Ubuntu 24.04 LTS.",
        "Configuração: 2 OCPUs (vCPUs) e 16 GB de Memória RAM.",
        "Performance otimizada para o backend Python/Flask."
    ])

    # Slide 4: Diagrama de Arquitetura (Placeholder)
    add_slide("Diagrama de Design System", is_image_slide=True)

    # Slide 5: Balanceamento de Carga
    add_slide("Distribuição de Tráfego", [
        "Serviço: OCI Flexible Load Balancer.",
        "Função: Receber conexões HTTPS e distribuir entre as VMs.",
        "Segurança: Terminação SSL/TLS integrada.",
        "Escalabilidade: Largura de banda mínima de 10Mbps (Always Free) ou superior."
    ])

    # Slide 6: Armazenamento e Biblioteca
    add_slide("Gestão de Arquivos e Dados", [
        "OCI Object Storage: Armazenamento de PDFs, Vídeos e Trabalhos (limite 100MB).",
        "Bucket S3-Compatible: Acesso rápido e custo extremamente baixo.",
        "Banco de Dados: OCI MySQL HeatWave ou PostgreSQL.",
        "Volume de Bloco: 50GB+ SSD (NVMe) para o sistema e logs."
    ])

    # Slide 7: Fluxo de Dados
    add_slide("Fluxo de Dados", [
        "1. Usuário faz requisição -> Load Balancer.",
        "2. LB direciona para a VM Ubuntu 24.04 (Instância Intel).",
        "3. Aplicação consulta DB (Dados) ou Object Storage (Mídia).",
        "4. Resposta enviada de volta ao usuário com compressão Gzip."
    ])

    # Slide 8: Justificativa Técnica
    add_slide("Justificativa da Escolha", [
        "VM Intel (Standard3): Melhor compatibilidade para bibliotecas x86_64 complexas.",
        "16GB RAM: Generoso para cache de banco de dados e buffers de vídeo.",
        "Ubuntu 24.04: Versão mais recente com 10 anos de suporte (LTS).",
        "OCI Load Balancer: Garante que o sistema não fique offline em picos de acesso."
    ])

    # Slide 9: Estimativa de Custos
    add_slide("Estimativa de Custos (OCI)", [
        "VM (2 vCPU / 16GB RAM): Aprox. $30 - $50/mês (ou no Free Tier dependendo da região).",
        "Load Balancer: Aprox. $18/mês.",
        "Object Storage (1TB): Aprox. $25/mês.",
        "Data Out (Tráfego): Primeiros 10TB são Gratuitos no OCI.",
        "Total Estimado: $70 - $100 mensais para escala profissional."
    ])

    # Slide 10: Conclusão
    add_slide("Próximos Passos", [
        "Configuração de Auto-scaling baseado em CPU.",
        "Implementação de WAF (Web Application Firewall).",
        "Setup de monitoramento com OCI Observability."
    ])

    save_path = "apresentacao/Arquitetura_AVA_OCI.pptx"
    prs.save(save_path)
    print(f"Apresentação gerada com sucesso em: {save_path}")

if __name__ == "__main__":
    create_presentation()
