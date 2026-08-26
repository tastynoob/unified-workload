# Shared settings for the AArch64 full-system GCPT SimPoint scripts.
# Edit this file only for a special-purpose run.

readonly INTERVAL=20000000
readonly WARMUP=20000000
readonly MEMORY=8G
readonly CPU_MODEL=neoverse-n1
readonly HARTS=1
readonly INSTRUCTION_COUNT=exact

readonly MAX_K=30
readonly NUM_INIT_SEEDS=2
readonly ITERS=1000
readonly SEED_KM=12345
readonly SEED_PROJ=67890
