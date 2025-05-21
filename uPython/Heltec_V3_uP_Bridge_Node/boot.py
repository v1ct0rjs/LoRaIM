# boot.py - Script que se ejecuta al iniciar el dispositivo
import gc
import machine
import time

# Configurar frecuencia de CPU para estabilidad
machine.freq(160000000)  # 160 MHz es más estable que 240 MHz

# Configurar el garbage collector para que se ejecute más agresivamente
gc.threshold(4096)  # Umbral más bajo para recolección más frecuente
gc.collect()

print("Boot: Iniciando sistema...")
print(f"Boot: Memoria libre: {gc.mem_free()} bytes")

# Verificar si hubo un reinicio por watchdog o error
reset_cause = machine.reset_cause()
if reset_cause == machine.HARD_RESET:
    print("Boot: Reinicio por hardware")
elif reset_cause == machine.SOFT_RESET:
    print("Boot: Reinicio por software")
elif reset_cause == machine.WDT_RESET:
    print("Boot: Reinicio por watchdog")
elif reset_cause == machine.DEEPSLEEP_RESET:
    print("Boot: Despertar de deep sleep")
else:
    print(f"Boot: Otro tipo de reinicio ({reset_cause})")

# Configurar el sistema para mayor estabilidad
import micropython
micropython.alloc_emergency_exception_buf(100)
