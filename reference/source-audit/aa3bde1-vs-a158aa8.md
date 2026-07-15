# Official OpenLA500 source audit

Official nested source: `aa3bde1f3e720e71c2c78d6b81930d797b810149` at `/home/toss-a-coin/WorkSpace/NSCSCC2026/chiplab/IP/myCPU`.
Historical team tree: `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6` in `/home/toss-a-coin/WorkSpace/NSCSCC2026/nscscc-cpu`.
The official tree is the default provenance; a158aa8 is diagnostic only.

## Classification counts

- official aa3 behavioral RTL: 21
- historical dead-or-backup: 2
- historical official-overlap: 20
- historical team-enhancement: 3

## Official files

| path | class | blob SHA1 | raw SHA256 | bytes |
| --- | --- | --- | --- | ---: |
| `IP/data_bank_sram.xcix` | official-memory-ip | `7312e3ea4ad93f196824d51450c3c913c5c7008a` | `ab1cd5714fa1cf94dd09fc59bc461bc92198a6e29e7aba07687f64dce696968f` | 11674557 |
| `IP/tagv_sram.xcix` | official-memory-ip | `e7fcbde4dbfa40b0d069b5c9f3a3526aa16b3a9a` | `0dfffef5a025f7ba266c7f7b1759c31951439c3fa0e93c522c2b8ad1dccc7941` | 11668860 |
| `LICENSE` | official-documentation | `ee5839968a2bf86c93283efc09d40fd050b7cfa2` | `6326ae60dd78c85b1f2f6ff308ef1615ff939323270d838e8ebab20f5de1a8c5` | 9719 |
| `README.md` | official-documentation | `beaa043a54d9aeae5c5fef9a097aaf594db7ff99` | `2f57d0abf4d73e93f1b8ded2a4543813d0b59f398415cd78922dfdcb96e1f14d` | 683 |
| `addr_trans.v` | official-behavioral-rtl | `e03fafbc6e05dc6a3abddc7808b58c24cb2875d8` | `b25c7585ca410363cbbb25e6669687083687fed1a0641a91ff58b7837c371697` | 8901 |
| `alu.v` | official-behavioral-rtl | `8569fe983adb5c08762964a2c44ec6db4831da75` | `5d73aa7f57367311f5d6f6fad5f750e5f97bc2bd1e52c7d0b9e543596ffc7d32` | 3066 |
| `axi_bridge.v` | official-behavioral-rtl | `4219790c25c653da1a061c5f4c674e062201b8e9` | `07c30c8e5e99373ecb988b2a5cc03e4e8cb7b6e22af26b1b37171a808b144f9e` | 10106 |
| `btb.v` | official-behavioral-rtl | `e2f6e340c1f4f98ce93493192030c32943935229` | `6d540a983075e8ed3a9bd1f791bc4ec14e3b08ff04c4c8f13ae1c0fa8a081bfb` | 6976 |
| `csr.h` | official-behavioral-rtl | `a1d8a4389e2b45afee520d5c70d728d14404e13c` | `11f5550b887a2b507a5b916340069d6d127848c66c761f07d0303c7cc201026d` | 1409 |
| `csr.v` | official-behavioral-rtl | `b43d83d7636f20ff05667ec4f439484c961f9090` | `7349b5b83975b6da8efe69f42d8ee43d93312f7e13def4ed2f6c48a3a868c433` | 25307 |
| `dcache.v` | official-behavioral-rtl | `d9c20456b28969fe32bfaf79cc79c2fba0db2e8a` | `8b6dd8088b8f2c09a20e8a6ce373c246b292558e7e225ff4c9210bf529553dfc` | 22880 |
| `div.v` | official-behavioral-rtl | `225827c7d69addd280cb671c17e067a406a9171f` | `7e499f4c43c92154d1d4e21be2f269ac140b4f2b2d944677c71f6f4213b66dc6` | 2642 |
| `doc/picture/框图.svg` | official-documentation | `734ecfe855957c7f259117b8e7e5ab57cdeae1c7` | `af55bd0cbc25e949031373a44c838bd9ca2c8176849a59a0c110bf7bdce9f908` | 74746 |
| `doc/分支预测.md` | official-documentation | `20d7d0b2e7a0c8bd70cc6dd84b255e4282350aef` | `bf3a4bf61595266f885f30e93e0dedab9adb5f403346082b559f2b0dc9ffa08f` | 11577 |
| `doc/前言.md` | official-documentation | `6e49d32cddb03566328b4712dc87651b982d0f49` | `041853727024bad0c8e2ddb0d2496fb6653e254e724d87aff585355a5a162059` | 1364 |
| `doc/设计概述.md` | official-documentation | `f93b5eba8fbb2fa014b1d6ed2e341a1603adea26` | `2a07d79593562549d37a0906d7742df11047fa802a1598fe04faaee7574a46cf` | 9165 |
| `exe_stage.v` | official-behavioral-rtl | `9c9d73033eeb00ce1f9e2e3db02010e99b851ba6` | `8e0df730dc433f4f173de2d781a3e3da45f781ef6bf1fdc7b82d9a4ddfb6cbd9` | 13681 |
| `icache.v` | official-behavioral-rtl | `5f641ae52220a8ef696b1ec8bc3a38e2a853a578` | `033c788597c9ed3664409c2c9df9d04e5a55a47316a33753b1e667c5589e5a48` | 14632 |
| `id_stage.v` | official-behavioral-rtl | `9bb80e2ee5155d229f64b8237138f92e9bfb4558` | `22ec5679f862d0736c36550e13aec72f2bd60eb4e824a3ad5d10b052b33edc2b` | 38058 |
| `if_stage.v` | official-behavioral-rtl | `f0684f133ffd509dcda14d6a29f03779822001e5` | `9fcc66200e549825c89737b420c68e97a22af1082e370536ad67e3d72e035547` | 12929 |
| `mem_stage.v` | official-behavioral-rtl | `ebeacf81c498b3041f5c55b16c2abe220e87ecd4` | `86592ed33afd5dde9e944860c7088ad70e5d62ee22f72999e336a64902d881a7` | 13988 |
| `mul.v` | official-behavioral-rtl | `9aa9e7ebf5632420a3cb6677fb873b62887cb71d` | `251d2bba3e659c294c9a004bbb2b542435fcfa0b0c1582cc1a7a3edca765a4c0` | 6045 |
| `mycpu.h` | official-behavioral-rtl | `6e3c073cbc09261c607acfa0b855edc0337b87c2` | `bebb41d58151b373980b9f666d9ca3c68dbfbcb070bc4dc84f96bc009fedcd6e` | 631 |
| `mycpu_top.v` | official-behavioral-rtl | `cff885ffa163fd4dba4e83d0db0f0e422fdce27e` | `0b2b294b1c242edc42bbaadd33c51125a1e24388c8781b0adad94aa25a4bdde1` | 44289 |
| `perf_counter.v` | official-behavioral-rtl | `7fa24d4cbe4429e7740dfc74c3b750819e057c90` | `a2f8f337422097699b91d217afb1eb896fa1aa02a7fdd1ed829c183de00935b6` | 1623 |
| `regfile.v` | official-behavioral-rtl | `3caa2b688d0b6cd2e37b28d43ab5fad632e7d2f7` | `e98d043d5166f8c2baf33692e74e3e2f203c8a80a3a2fae6b0f913ffb45d1203` | 872 |
| `tlb_entry.v` | official-behavioral-rtl | `0dad79a3947675efc2115a10d6dfcbdbb4038a5a` | `a3e3508a0c755375336ba6db392f9038e1d793042fc21b7cd088fde9febcba1f` | 9268 |
| `tools.v` | official-behavioral-rtl | `28022d1fc25026db3282f2cfae319e8b0158d55f` | `8dd00f9bef99547bdf97c60dbbce2a792a8de574f2ffcace7775ffcf29f9d531` | 2696 |
| `wb_stage.v` | official-behavioral-rtl | `90ae54b4ea13298aa64ee83aa33eee14813392d7` | `8a6f6cb282d152e4b43673397b8c00f598e3d116589e5797fb6feaadbc032a09` | 12315 |

## Historical comparison

| path | class | official basename | historical SHA256 | official SHA256 |
| --- | --- | --- | --- | --- |
| `rtl/addr_trans.v` | official-overlap | `addr_trans.v` | `b25c7585ca410363cbbb25e6669687083687fed1a0641a91ff58b7837c371697` | `b25c7585ca410363cbbb25e6669687083687fed1a0641a91ff58b7837c371697` |
| `rtl/alu.v` | official-overlap | `alu.v` | `5d73aa7f57367311f5d6f6fad5f750e5f97bc2bd1e52c7d0b9e543596ffc7d32` | `5d73aa7f57367311f5d6f6fad5f750e5f97bc2bd1e52c7d0b9e543596ffc7d32` |
| `rtl/axi_bridge.v` | official-overlap | `axi_bridge.v` | `07c30c8e5e99373ecb988b2a5cc03e4e8cb7b6e22af26b1b37171a808b144f9e` | `07c30c8e5e99373ecb988b2a5cc03e4e8cb7b6e22af26b1b37171a808b144f9e` |
| `rtl/btb.v` | official-overlap | `btb.v` | `81b34945ad638d6211301aafe48cfd22344933ba9c66f56e7c0472d24bf47ae9` | `6d540a983075e8ed3a9bd1f791bc4ec14e3b08ff04c4c8f13ae1c0fa8a081bfb` |
| `rtl/btb.v.bak` | dead-or-backup | `` | `6d540a983075e8ed3a9bd1f791bc4ec14e3b08ff04c4c8f13ae1c0fa8a081bfb` | `` |
| `rtl/csr.h` | official-overlap | `csr.h` | `11f5550b887a2b507a5b916340069d6d127848c66c761f07d0303c7cc201026d` | `11f5550b887a2b507a5b916340069d6d127848c66c761f07d0303c7cc201026d` |
| `rtl/csr.v` | official-overlap | `csr.v` | `7349b5b83975b6da8efe69f42d8ee43d93312f7e13def4ed2f6c48a3a868c433` | `7349b5b83975b6da8efe69f42d8ee43d93312f7e13def4ed2f6c48a3a868c433` |
| `rtl/dcache.v` | official-overlap | `dcache.v` | `8c9c968723710ca741bb5253cc0a1f29c9c6f9f8b3e5e2b14b69f11483e60e97` | `8b6dd8088b8f2c09a20e8a6ce373c246b292558e7e225ff4c9210bf529553dfc` |
| `rtl/div.v` | official-overlap | `div.v` | `7e499f4c43c92154d1d4e21be2f269ac140b4f2b2d944677c71f6f4213b66dc6` | `7e499f4c43c92154d1d4e21be2f269ac140b4f2b2d944677c71f6f4213b66dc6` |
| `rtl/exe_stage.v` | official-overlap | `exe_stage.v` | `cab20e05205c6bddff19f01fd15ad4cb671144debf0836982b45b334c686f526` | `8e0df730dc433f4f173de2d781a3e3da45f781ef6bf1fdc7b82d9a4ddfb6cbd9` |
| `rtl/icache.v` | official-overlap | `icache.v` | `85ba1acc69616dd8b19dae1578fc7e002c83fd435f90227f54068e4fa492675b` | `033c788597c9ed3664409c2c9df9d04e5a55a47316a33753b1e667c5589e5a48` |
| `rtl/id_stage.v` | official-overlap | `id_stage.v` | `dcd896a12fda42faff9f7c1bcd43de3bbd7bb181be688b0cef21dded5e05d807` | `22ec5679f862d0736c36550e13aec72f2bd60eb4e824a3ad5d10b052b33edc2b` |
| `rtl/if_stage.v` | official-overlap | `if_stage.v` | `9fcc66200e549825c89737b420c68e97a22af1082e370536ad67e3d72e035547` | `9fcc66200e549825c89737b420c68e97a22af1082e370536ad67e3d72e035547` |
| `rtl/lacc_core.v` | team-enhancement | `` | `0b17abbd83cbbf088993dcb30a38981e99d600ebaeaa5c566ad4eaff75ac97b5` | `` |
| `rtl/lacc_demo.v` | team-enhancement | `` | `8cae09cc7f0acb0ea5cc24352704d80baf116e29f4ae372ca9eac6b63bac2ea0` | `` |
| `rtl/mem_stage.v` | official-overlap | `mem_stage.v` | `86592ed33afd5dde9e944860c7088ad70e5d62ee22f72999e336a64902d881a7` | `86592ed33afd5dde9e944860c7088ad70e5d62ee22f72999e336a64902d881a7` |
| `rtl/mul.v` | official-overlap | `mul.v` | `251d2bba3e659c294c9a004bbb2b542435fcfa0b0c1582cc1a7a3edca765a4c0` | `251d2bba3e659c294c9a004bbb2b542435fcfa0b0c1582cc1a7a3edca765a4c0` |
| `rtl/mycpu_top.v` | official-overlap | `mycpu_top.v` | `ff286f559dbc9131349c9fb8c842110569d231b6a34e76ded172c403d8f90afa` | `0b2b294b1c242edc42bbaadd33c51125a1e24388c8781b0adad94aa25a4bdde1` |
| `rtl/perf_counter.v` | official-overlap | `perf_counter.v` | `a2f8f337422097699b91d217afb1eb896fa1aa02a7fdd1ed829c183de00935b6` | `a2f8f337422097699b91d217afb1eb896fa1aa02a7fdd1ed829c183de00935b6` |
| `rtl/regfile.v` | official-overlap | `regfile.v` | `e98d043d5166f8c2baf33692e74e3e2f203c8a80a3a2fae6b0f913ffb45d1203` | `e98d043d5166f8c2baf33692e74e3e2f203c8a80a3a2fae6b0f913ffb45d1203` |
| `rtl/regfile_dual.v` | dead-or-backup | `` | `7c90b96fdedca94154a19c650d2c60423e62b784abd355d37a1db26f0d14a9a3` | `` |
| `rtl/store_buffer.v` | team-enhancement | `` | `3e946de3edd58763df8b459a53b9f513d5d25619c7f270d81f63a92017b85040` | `` |
| `rtl/tlb_entry.v` | official-overlap | `tlb_entry.v` | `a3e3508a0c755375336ba6db392f9038e1d793042fc21b7cd088fde9febcba1f` | `a3e3508a0c755375336ba6db392f9038e1d793042fc21b7cd088fde9febcba1f` |
| `rtl/tools.v` | official-overlap | `tools.v` | `0160c1b8a80f09670a0cc1942b72b44350a4d79d1866fdaa5eb4ea8fa77e9bef` | `8dd00f9bef99547bdf97c60dbbce2a792a8de574f2ffcace7775ffcf29f9d531` |
| `rtl/wb_stage.v` | official-overlap | `wb_stage.v` | `8a6f6cb282d152e4b43673397b8c00f598e3d116589e5797fb6feaadbc032a09` | `8a6f6cb282d152e4b43673397b8c00f598e3d116589e5797fb6feaadbc032a09` |

## Default-profile conclusion

The default profile must source behavior from SpinalHDL generated `core_top`;
official aa3 functionality is the reference contract. LACC, store buffer,
backup, and unmatched historical files remain optional or diagnostic and are
not part of the official default generation or acceptance claim.
