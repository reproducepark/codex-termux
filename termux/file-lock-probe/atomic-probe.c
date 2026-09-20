#include <stdatomic.h>
#include <stdint.h>

int termux_atomic_probe(void) {
    _Atomic uint32_t count = 3;
    _Atomic uint64_t flags = 0;
    uint32_t expected = 4;
    if (atomic_fetch_add_explicit(&count, 1, memory_order_relaxed) != 3) return 1;
    if (!atomic_compare_exchange_strong_explicit(
            &count, &expected, 5, memory_order_acq_rel, memory_order_acquire)) return 2;
    if (atomic_fetch_sub_explicit(&count, 1, memory_order_release) != 5) return 3;
    if (atomic_fetch_or_explicit(&flags, 8, memory_order_acq_rel) != 0) return 4;
    if (atomic_fetch_add_explicit(&flags, 2, memory_order_acquire) != 8) return 5;
    if (atomic_fetch_add_explicit(&flags, 1, memory_order_relaxed) != 10) return 6;
    if (atomic_fetch_sub_explicit(&flags, 1, memory_order_release) != 11) return 7;
    if (atomic_fetch_add_explicit(&count, 1, memory_order_acq_rel) != 4) return 8;
    if (atomic_fetch_or_explicit(&flags, 16, memory_order_release) != 10) return 9;
    return atomic_load(&count) == 5 && atomic_load(&flags) == 26 ? 0 : 10;
}
