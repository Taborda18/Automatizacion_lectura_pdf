import os
import re
import shutil
import fitz
import easyocr

RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETA_GRUPOS = os.path.join(RAIZ, 'Grupos')

reader = easyocr.Reader(['es'], gpu=False, verbose=False)

PATRONES = [
    re.compile(r'[Nn][uú]mero\s+de\s+documento[:\s]+(\d{6,12})', re.IGNORECASE),
    re.compile(r'N[UÚ]MERO\s+DE\s+IDENTIFIC\w+\s+(\d{6,12})', re.IGNORECASE),
    re.compile(r'N[UÚ]MERO\s+DE\s+(\d{6,12})\s+IDENTIFIC', re.IGNORECASE),
    re.compile(r'C[EÉ]DULA\s+DE\s+CIUDADAN[IÍ]A\s+n[uú]mero\s+(\d{6,12})', re.IGNORECASE),
    re.compile(r'NUMER[OÓ]\s+([\d]{2,3}[.\s][\d]{3}[.\s][\d]{3})', re.IGNORECASE),
    re.compile(r'(?:CIUDADAN[IÍ]A|PERSONAL)\s+([\d]{2}[\s.,][\d]{3}[\s.,][\d]{3})', re.IGNORECASE),
]


def limpiar_numero(raw):
    return re.sub(r'[\s.,]', '', raw)


def extraer_cc(pdf_path):
    doc = fitz.open(pdf_path)
    for i in reversed(range(len(doc))):
        page = doc[i]
        pix = page.get_pixmap(dpi=200)
        result = reader.readtext(pix.tobytes("png"), detail=0)
        texto = " ".join(result)
        for patron in PATRONES:
            match = patron.search(texto)
            if match:
                cc = limpiar_numero(match.group(1))
                if 6 <= len(cc) <= 12:
                    doc.close()
                    return cc
    doc.close()
    return None


def procesar_grupo(carpeta_grupo):
    nombre_grupo = os.path.basename(carpeta_grupo)
    destino = os.path.join(RAIZ, f"Renombrados {nombre_grupo}")
    os.makedirs(destino, exist_ok=True)

    pdfs = sorted(f for f in os.listdir(carpeta_grupo) if f.upper().endswith('.PDF'))
    if not pdfs:
        print(f"  Sin PDFs, saltando.\n")
        return 0, 0, []

    print(f"  PDFs encontrados: {len(pdfs)}")
    exitos = 0
    fallos = []
    for pdf in pdfs:
        ruta = os.path.join(carpeta_grupo, pdf)
        print(f"    {pdf} ...", end=" ")
        try:
            cc = extraer_cc(ruta)
        except Exception as e:
            print(f"-> ERROR: {e}")
            fallos.append((pdf, f"Error al procesar: {e}"))
            continue
        if cc:
            nuevo_nombre = f"CC.{cc}.PDF"
            nueva_ruta = os.path.join(destino, nuevo_nombre)
            if os.path.exists(nueva_ruta):
                contador = 2
                while os.path.exists(nueva_ruta):
                    nuevo_nombre = f"CC.{cc}_{contador}.PDF"
                    nueva_ruta = os.path.join(destino, nuevo_nombre)
                    contador += 1
            shutil.copy2(ruta, nueva_ruta)
            print(f"-> {nuevo_nombre}")
            exitos += 1
        else:
            print("-> NO se encontro CC")
            fallos.append((pdf, "No se encontro numero de CC en ninguna pagina del PDF"))

    print(f"  Resultado: {exitos}/{len(pdfs)}\n")

    reporte = os.path.join(destino, "auditoria.txt")
    with open(reporte, 'w', encoding='utf-8') as f:
        f.write(f"REPORTE DE AUDITORÍA - {nombre_grupo}\n")
        f.write("=" * 50 + "\n")
        f.write(f"Carpeta origen: {carpeta_grupo}\n")
        f.write(f"Total PDFs: {len(pdfs)}\n")
        f.write(f"Renombrados exitosamente: {exitos}\n")
        f.write(f"No renombrados: {len(fallos)}\n\n")
        if fallos:
            f.write("ARCHIVOS NO RENOMBRADOS\n")
            f.write("-" * 50 + "\n")
            for nombre, motivo in fallos:
                f.write(f"Archivo: {nombre}\n")
                f.write(f"Motivo:  {motivo}\n\n")
        else:
            f.write("Todos los PDFs fueron renombrados correctamente.\n")

    return len(pdfs), exitos, fallos


def main():
    if not os.path.isdir(CARPETA_GRUPOS):
        print(f"No se encontró la carpeta 'Grupos' en: {RAIZ}")
        return

    grupos = sorted(
        d for d in os.listdir(CARPETA_GRUPOS)
        if os.path.isdir(os.path.join(CARPETA_GRUPOS, d))
    )

    if not grupos:
        print("No se encontraron subcarpetas en Grupos.")
        return

    print(f"Raíz: {RAIZ}")
    print(f"Grupos encontrados: {len(grupos)}\n")

    total_pdfs = 0
    total_exitos = 0
    total_fallos = 0
    for grupo in grupos:
        ruta_grupo = os.path.join(CARPETA_GRUPOS, grupo)
        print(f"[{grupo}]")
        pdfs, exitos, fallos = procesar_grupo(ruta_grupo)
        total_pdfs += pdfs
        total_exitos += exitos
        total_fallos += len(fallos)

    print("=" * 50)
    print(f"TOTAL: {total_exitos}/{total_pdfs} renombrados en {len(grupos)} grupos")
    if total_fallos:
        print(f"       {total_fallos} no renombrados (ver auditoria.txt en cada carpeta)")


if __name__ == '__main__':
    main()
