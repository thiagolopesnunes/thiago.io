from flask import Flask, render_template, request, send_from_directory
import os
import xml.etree.ElementTree as ET
from datetime import datetime

app = Flask(__name__)

# Configuração das pastas de upload e processamento
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Criar diretórios se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def process_xml(file_path):
    """
    Processa um arquivo XML TISS, extraindo protocolos e gerando novos arquivos.
    """
    # Registrar namespace ANS
    ET.register_namespace('ans', 'http://www.ans.gov.br/padroes/tiss/schemas')
    
    # Parse do arquivo original
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Encontrar todos os protocolos
    protocolos = root.findall('.//{http://www.ans.gov.br/padroes/tiss/schemas}dadosProtocolo')
    
    # Capturar hash do arquivo original
    hash_original = None
    hash_element = root.find('.//ans:epilogo/ans:hash', namespaces={'ans': 'http://www.ans.gov.br/padroes/tiss/schemas'})
    if hash_element is not None:
        hash_original = hash_element.text.strip()

    generated_files = []
    
    for protocolo in protocolos:
        # Criar nova estrutura base do arquivo processado
        new_root = ET.fromstring("""<?xml version="1.0" encoding="ISO-8859-1"?>
        <ans:mensagemTISS xmlns:ans="http://www.ans.gov.br/padroes/tiss/schemas">
            <ans:cabecalho/>
            <ans:operadoraParaPrestador>
                <ans:demonstrativosRetorno>
                    <ans:demonstrativoAnaliseConta>
                        <ans:cabecalhoDemonstrativo/>
                        <ans:dadosPrestador/>
                        <ans:dadosConta/>
                    </ans:demonstrativoAnaliseConta>
                </ans:demonstrativosRetorno>
            </ans:operadoraParaPrestador>
            <ans:epilogo/>
        </ans:mensagemTISS>""")
        
        # Copiar o cabeçalho original para o novo XML
        cabecalho_orig = root.find('ans:cabecalho', namespaces={'ans': 'http://www.ans.gov.br/padroes/tiss/schemas'})
        cabecalho_new = new_root.find('ans:cabecalho', namespaces={'ans': 'http://www.ans.gov.br/padroes/tiss/schemas'})
        if cabecalho_orig is not None and cabecalho_new is not None:
            cabecalho_new.extend(list(cabecalho_orig))

        # Copiar o cabeçalho do demonstrativo corretamente
        cabecalho_demonstrativo_orig = root.find('.//ans:cabecalhoDemonstrativo', namespaces={'ans': 'http://www.ans.gov.br/padroes/tiss/schemas'})
        cabecalho_demonstrativo_new = new_root.find('.//ans:cabecalhoDemonstrativo', namespaces={'ans': 'http://www.ans.gov.br/padroes/tiss/schemas'})

        if cabecalho_demonstrativo_orig is not None and cabecalho_demonstrativo_new is not None:
            cabecalho_demonstrativo_new.extend(list(cabecalho_demonstrativo_orig))

        # Extrair número do protocolo
        numero_protocolo = protocolo.find('ans:numeroProtocolo', namespaces={'ans': 'http://www.ans.gov.br/padroes/tiss/schemas'}).text

        # Criar nome do arquivo
        filename = f"zgTISS3_{numero_protocolo}_21000041_04201372000137_ANALISE_CONTA_{datetime.now().strftime('%m_%Y')}_{numero_protocolo}.xml"
        
        # Adicionar dados do protocolo no novo XML
        dados_conta_new = new_root.find('.//ans:dadosConta', namespaces={'ans': 'http://www.ans.gov.br/padroes/tiss/schemas'})
        if dados_conta_new is not None:
            dados_conta_new.append(protocolo)

        # Inserir o hash original dentro de <ans:epilogo>
        epilogo = new_root.find('.//ans:epilogo', namespaces={'ans': 'http://www.ans.gov.br/padroes/tiss/schemas'})
        if epilogo is not None and hash_original:
            hash_element = ET.Element('{http://www.ans.gov.br/padroes/tiss/schemas}hash')
            hash_element.text = hash_original
            epilogo.append(hash_element)

        # Salvar arquivo processado
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        ET.ElementTree(new_root).write(output_path, encoding='ISO-8859-1', xml_declaration=True)
        
        generated_files.append(filename)
    
    return generated_files

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """
    Página inicial para upload de arquivos XML.
    """
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'Nenhum arquivo enviado'
        
        file = request.files['file']
        if file.filename == '':
            return 'Nome de arquivo inválido'
        
        if file and file.filename.endswith('.xml'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            
            generated_files = process_xml(file_path)
            
            return render_template('results.html', files=generated_files)
    
    return render_template('upload.html')

@app.route('/download/<filename>')
def download_file(filename):
    """
    Rota para baixar arquivos processados.
    """
    return send_from_directory(
        app.config['PROCESSED_FOLDER'],
        filename,
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True)
