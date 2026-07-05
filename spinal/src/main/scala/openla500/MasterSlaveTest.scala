package openla500
import spinal.core._
import spinal.lib._

case class StreamIO() extends Bundle with IMasterSlave {
  val valid = Bool(); val ready = Bool(); val data = UInt(8 bits)
  override def asMaster(): Unit = { out(valid, data); in(ready) }
}
class Producer extends Component {
  val io = master port StreamIO()
  io.valid := True; io.data := 42
}
class Consumer extends Component {
  val io = slave port StreamIO()
  val r = Reg(UInt(8 bits)); io.ready := True
  when(io.valid && io.ready) { r := io.data }
}
class Connected extends Component {
  val prod = new Producer
  val cons = new Consumer
  prod.io <> cons.io  // Auto-connect master↔slave
}
object GenConnected extends App {
  SpinalConfig(targetDirectory = "../rtl").generateVerilog(new Connected)
}
