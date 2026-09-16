"""Build on macOS only: python scripts/build_macos.py (native architecture)."""
import hashlib
import platform
import subprocess
import sys
from pathlib import Path


def main():
    if sys.platform != 'darwin':raise SystemExit('macOS .app must be built on macOS.')
    root = Path(__file__).resolve().parent.parent
    build = root / 'build'
    build.mkdir(exist_ok=True)
    from PIL import Image
    with Image.open(root / 'assets/app-icon.png') as image:
        image.convert('RGBA').resize((1024, 1024)).save(build / 'app-icon.icns')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--onedir', '--windowed', '--name', 'CodexQuotaResume',
                    '--osx-bundle-identifier', 'com.codexquota.desktop',
                    '--icon', str(build / 'app-icon.icns'),
                    '--add-data', str(root / 'assets/github-mark.png') + ':.',
                    '--hidden-import', 'AppKit', '--hidden-import', 'Foundation',
                    '--distpath', str(root / 'dist'), '--workpath', str(build),
                    '--specpath', str(build), str(root / 'scripts/app.py')], check=True, cwd=root)
    bundle = root / 'dist/CodexQuotaResume.app'
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
    archive = root / f'dist/CodexQuotaResume-macOS-{platform.machine()}-preview.zip'
    subprocess.run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(bundle), str(archive)], check=True)
    archive.with_suffix('.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    print(archive)


if __name__ == '__main__':main()
