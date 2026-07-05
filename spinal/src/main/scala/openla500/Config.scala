package openla500

import spinal.core._
import spinal.lib._

// CSRs from csr.h
object CSR {
  val CRMD    = 0x0
  val PRMD    = 0x1
  val EUEN    = 0x2
  val ECFG    = 0x4
  val ESTAT   = 0x5
  val ERA     = 0x6
  val BADV    = 0x7
  val EENTRY  = 0xC
  val TLBIDX  = 0x10
  val TLBEHI  = 0x11
  val TLBELO0 = 0x12
  val TLBELO1 = 0x13
  val ASID    = 0x18
  val PGDL    = 0x19
  val PGDH    = 0x1A
  val SAVE0   = 0x30
  val SAVE1   = 0x31
  val SAVE2   = 0x32
  val SAVE3   = 0x33
  val TID     = 0x40
  val TCFG    = 0x41
  val TVAL    = 0x42
  val TICLR   = 0x44
}

// UART register offsets (16550-compatible)
object UartOffset {
  val RBR = 0  // Receive Buffer (DLAB=0)
  val THR = 0  // Transmit Holding (DLAB=0)
  val DLL = 0  // Divisor Latch LSB (DLAB=1)
  val IER = 1  // Interrupt Enable (DLAB=0)
  val DLM = 1  // Divisor Latch MSB (DLAB=1)
  val IIR = 2  // Interrupt Identification
  val FCR = 2  // FIFO Control
  val LCR = 3  // Line Control
  val MCR = 4  // Modem Control
  val LSR = 5  // Line Status
  val MSR = 6  // Modem Status
  val SCR = 7  // Scratch
}

object ConfRegAddr {
  val CR0           = 0x8000  // bfaf_8000
  val CR1           = 0x8010  // bfaf_8010
  val LED_ADDR      = 0xf020  // bfaf_f020
  val LED_RG0_ADDR  = 0xf030  // bfaf_f030
  val LED_RG1_ADDR  = 0xf040  // bfaf_f040
  val NUM_ADDR      = 0xf050  // bfaf_f050
  val SWITCH_ADDR   = 0xf060  // bfaf_f060
  val TIMER_ADDR    = 0xe000  // bfaf_e000
  val IO_SIMU_ADDR  = 0xff00  // bfaf_ff00
  val VIRTUAL_UART  = 0xff10  // bfaf_ff10
  val SIMU_FLAG     = 0xff20  // bfaf_ff20
  val OPEN_TRACE    = 0xff30  // bfaf_ff30
  val NUM_MONITOR   = 0xff40  // bfaf_ff40
}

object MemMap {
  val RESET_VECTOR  = 0x1c000000L
  val UART_BASE     = 0xbfe001e0L
  val CONFREG_BASE  = 0xbfaf0000L
  val UART_PHYS     = 0x1fe001e0L
  val CONFREG_PHYS  = 0x1faf0000L
}

object CacheConfig {
  val ICACHE_SIZE   = 8192       // 8KB
  val ICACHE_WAYS   = 2
  val ICACHE_LINE   = 16         // bytes per line
  val ICACHE_SETS   = 256        // 8KB / (2 ways * 16B)
  val ICACHE_INDEX  = 8          // log2(256)
  val ICACHE_OFFSET = 4          // log2(16)
  val ICACHE_TAG    = 20         // 32 - 8 - 4

  val DCACHE_SIZE   = 8192
  val DCACHE_WAYS   = 2
  val DCACHE_LINE   = 16
  val DCACHE_SETS   = 256
  val DCACHE_INDEX  = 8
  val DCACHE_OFFSET = 4
  val DCACHE_TAG    = 20
}

object BTBConfig {
  val ENTRIES = 32
  val INDEX_BITS = 5  // log2(32)
}

object TLBConfig {
  val ENTRIES = 32
  val INDEX_BITS = 5
}
