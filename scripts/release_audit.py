"""Fail-closed release package scanner. Run against a CLEAN distribution folder."""
from pathlib import Path
import re, sys
root = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
forbidden_dirs = {'.git', '.venv', 'venv', 'node_modules', 'dist', 'build', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'research', 'backups'}
forbidden_names = {'.env', '.env.local', '.env.production', 'id_rsa', 'id_ed25519'}
forbidden_suffixes = {'.pyc','.db','.sqlite','.sqlite3','.xlsx','.xls','.xlsm','.pkl','.log','.pem','.key','.zip','.bak','.backup'}
private_patterns = [r'\bfinnhub\b',r'\bvcp\b',r'mean[_ -]?reversion',r'consolidation[_ -]?box',r'ema[_ -]?pullback',r'frozen[_ -]?config']
secret_patterns = [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*[\"\']?[a-z0-9_\-]{20,}',r'(?i)ghp_[a-z0-9]{30,}',r'(?i)sk-[a-z0-9]{24,}']
text_exts={'.py','.md','.txt','.toml','.json','.tsx','.ts','.css','.html','.yaml','.yml','.example','.bat','.sh','.gitignore'}
findings=[]
for path in sorted(root.rglob('*')):
    rel=path.relative_to(root)
    if any(part in forbidden_dirs for part in rel.parts):
        findings.append(f'Forbidden directory in release: {rel}')
        continue
    if not path.is_file(): continue
    if path.name in forbidden_names or path.suffix.lower() in forbidden_suffixes:
        findings.append(f'Forbidden file in release: {rel}')
        continue
    if path.suffix.lower() not in text_exts and path.name not in {'.gitignore','LICENSE'}:
        findings.append(f'Unreviewed file type: {rel}')
        continue
    content=path.read_text(encoding='utf-8',errors='replace')
    if rel.as_posix()=='scripts/release_audit.py': continue
    for pattern in private_patterns+secret_patterns:
        if re.search(pattern,content,re.I):
            findings.append(f'Pattern {pattern} in {rel}')
print('\n'.join(findings) if findings else 'PASS: Strict release package audit')
sys.exit(bool(findings))
