# Instruções para Conversão PDF

## Opção 1: Usando Pandoc (Recomendado)

```bash
# Instalar pandoc (se não instalado)
# Windows: https://pandoc.org/installing.html
# Linux: sudo apt-get install pandoc
# macOS: brew install pandoc

# Converter MD para PDF
pandoc ENTREGA-FINAL.md -o ENTREGA-FINAL.pdf --pdf-engine=wkhtmltopdf
```

## Opção 2: Usando VSCode

1. Instalar extensão "Markdown PDF"
2. Abrir ENTREGA-FINAL.md
3. Ctrl+Shift+P -> "Markdown PDF: Export (pdf)"

## Opção 3: Online

1. Abrir https://md2pdf.netlify.app/
2. Upload do arquivo ENTREGA-FINAL.md
3. Download do PDF gerado

## Opção 4: GitHub Pages

1. Push para repositório GitHub
2. Usar GitHub Pages para renderizar
3. Print to PDF no browser
