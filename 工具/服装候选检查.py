"""刷新并核验独立服装候选登记，不改变角色母版或生产任务。"""
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / '资产/服装候选'
REGISTRY = FOLDER / '登记.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    data = json.loads(REGISTRY.read_text(encoding='utf-8'))
    ids = set()
    for row in data['assets']:
        assert row['id'] not in ids, row['id']
        ids.add(row['id'])
        ref = ROOT / f"参考/用户媒体/服装群像/{row['source_image']}-照片-{row['source_image']}.jpg"
        assert ref.is_file(), ref
        row['source_path'] = ref.relative_to(ROOT).as_posix()
        row['source_sha256'] = sha(ref)
        image = FOLDER / row['image']
        if image.exists():
            raw = image.read_bytes()
            assert raw[:8] == b'\x89PNG\r\n\x1a\n', image
            pos, end, compressed = 8, False, []
            while pos < len(raw):
                size = struct.unpack('>I', raw[pos:pos + 4])[0]
                kind = raw[pos + 4:pos + 8]
                payload = raw[pos + 8:pos + 8 + size]
                crc = struct.unpack('>I', raw[pos + 8 + size:pos + 12 + size])[0]
                assert zlib.crc32(kind + payload) & 0xffffffff == crc, image
                if kind == b'IHDR':
                    width, height = struct.unpack('>II', payload[:8])
                    row.update(width=width, height=height, format='PNG')
                if kind == b'IDAT':
                    compressed.append(payload)
                if kind == b'IEND':
                    end = True
                    break
                pos += size + 12
            assert end and zlib.decompress(b''.join(compressed)), image
            row.update(sha256=sha(image), status='generated_candidate')
        else:
            assert row['status'] == 'pending_generation', image
    REGISTRY.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    complete = sum(row['status'] == 'generated_candidate' for row in data['assets'])
    print(f'服装候选：{complete}/{len(ids)} 张已生成；来源与图像完整性核验通过。')
    return data

if __name__ == '__main__':
    main()
