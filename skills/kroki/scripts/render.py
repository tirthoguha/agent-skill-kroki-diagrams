#!/usr/bin/env python3
"""Render Mermaid with local Kroki; validate before replacing output files."""
import argparse
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
ET.register_namespace('xhtml', 'http://www.w3.org/1999/xhtml')


def opaque_svg(data):
    root = ET.fromstring(data)
    if root.tag != '{%s}svg' % SVG:
        raise ValueError('Renderer did not return an SVG document')
    viewbox = root.get('viewBox')
    if not viewbox:
        raise ValueError('SVG is missing its scalable viewBox')
    values = viewbox.replace(',', ' ').split()
    if len(values) != 4:
        raise ValueError('Invalid SVG viewBox')
    x, y, width, height = map(float, values)
    if width <= 0 or height <= 0:
        raise ValueError('Invalid SVG dimensions')
    rect = ET.Element('{%s}rect' % SVG, {
        'x': str(x), 'y': str(y), 'width': str(width), 'height': str(height),
        'style': 'fill:#ffffff;stroke:none', 'aria-hidden': 'true',
    })
    root.insert(0, rect)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def opaque_png(data, directory):
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Renderer did not return PNG data')
    raw = directory / 'raw.png'
    output = directory / 'opaque.png'
    raw.write_bytes(data)
    im = shutil.which('magick') or shutil.which('convert')
    if im:
        subprocess.run([im, str(raw), '-background', 'white', '-alpha', 'remove',
                        '-alpha', 'off', 'PNG24:' + str(output)], check=True)
    else:
        try:
            from PIL import Image
        except ImportError:
            if not shutil.which('sips'):
                raise RuntimeError('PNG needs ImageMagick, Pillow, or macOS sips; SVG does not.')
            print('Using JPEG fallback: install Pillow or ImageMagick for lossless PNG.', file=sys.stderr)
            jpeg = directory / 'flatten.jpg'
            subprocess.run(['sips', '-s', 'format', 'jpeg', str(raw), '--out', str(jpeg)], check=True, stdout=subprocess.DEVNULL)
            subprocess.run(['sips', '-s', 'format', 'png', str(jpeg), '--out', str(output)], check=True, stdout=subprocess.DEVNULL)
        else:
            with Image.open(io.BytesIO(data)) as source:
                rgba = source.convert('RGBA')
            result = Image.new('RGB', rgba.size, 'white')
            result.paste(rgba, mask=rgba.getchannel('A'))
            result.save(output)
    result = output.read_bytes()
    if len(result) < 26 or not result.startswith(b'\x89PNG\r\n\x1a\n') or result[25] != 2:
        raise ValueError('Flattening did not produce an RGB PNG')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--format', choices=['png', 'svg', 'both'], default='png')
    parser.add_argument('--out-dir', type=Path, help='Defaults to the source directory')
    parser.add_argument('--port', type=int, default=os.environ.get('KROKI_PORT', '8585'))
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port must be between 1 and 65535')
    source = args.source.resolve()
    source.read_text(encoding='utf-8')  # Fail before creating outputs if source is unreadable.
    destination = (args.out_dir or source.parent).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    formats = ['png', 'svg'] if args.format == 'both' else [args.format]
    with tempfile.TemporaryDirectory(prefix='.kroki-', dir=destination) as tmp:
        directory = Path(tmp)
        staged = []
        for fmt in formats:
            raw = directory / ('response.' + fmt)
            url = 'http://localhost:%s/mermaid/%s' % (args.port, fmt)
            if fmt == 'png':
                url += '?bgColor=white'
            subprocess.run(['curl', '--fail', '--show-error', '--silent',
                            '--connect-timeout', '5', '--max-time', '60', '-X', 'POST', url,
                            '-H', 'Content-Type: text/plain', '--data-binary', '@' + str(source),
                            '-o', str(raw)], check=True)
            data = raw.read_bytes()
            rendered = opaque_svg(data) if fmt == 'svg' else opaque_png(data, directory)
            prepared = directory / ('validated.' + fmt)
            prepared.write_bytes(rendered)
            staged.append((prepared, destination / (source.stem + '.' + fmt)))
        # Only start replacing outputs after all requested formats have validated.
        for prepared, target in staged:
            os.replace(prepared, target)
            print(target)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, ET.ParseError, subprocess.CalledProcessError) as error:
        print('Render failed: %s' % error, file=sys.stderr)
        sys.exit(1)
