# 検証スナップショット

Version: v2026.07.23.1

取得元: `kelly-vps:C:\keiba\data`

サーバー側整合スナップショット:
`C:\keiba\backup\market_edge_research_20260723_snapshot`

PC側保存先:
`market_edge_research_20260723\data`

## ファイル

| ファイル | サイズ（bytes） | SHA-256 |
|---|---:|---|
| `ai_index_jra.sqlite` | 35,946,496 | `cf2ed03080a22b9eea01e6dcf18a0e5b0de43231034d2f7c7dc2eab30717b3ff` |
| `ai_index_local.sqlite` | 107,384,832 | `d8353dda56d16df815dee56485cb9b1d27a2053274c7f0e54511684482d80ee2` |
| `features_jra.sqlite` | 65,601,536 | `0e79c594119d3dc477a9a0a5c6de6bb81e803c63f5f5bd871b56521a764717a0` |
| `features_local.sqlite` | 220,479,488 | `d6c8924722e222f00f375e0f7f5be7206095e97d940ff1a86122c09a512f3a68` |
| `keiba_jra.sqlite` | 98,381,824 | `20c8aa350689465d1f0dc6436c7ac33c0353fb8e298f40120000c33377b3d4e3` |
| `keiba_local.sqlite` | 301,428,736 | `848af3f957f0e7d9a231ffc0ef836c82905b6607b15f9ab1a869e50e21e0333e` |
| `pedigree_jra.json` | 5,823,192 | `bb3827c7702c135df6f74c915c16769dd8a478ed8a856ade96522198edf00875` |
| `training_jra.json` | 111,392,470 | `befceaf6f51d58823be9efba946ae914eaf85d5a896e4d8e71cb6832c652d886` |

## 検証結果

- SQLite 6ファイル: `PRAGMA integrity_check = ok`
- `training_jra.json`: 13,101頭
- `pedigree_jra.json`: 13,101頭
- サーバー上の元DBは未変更

