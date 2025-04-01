# Documentación del Bot de Trading Automático con Grid Trading Adaptativo

## Introducción

Este documento proporciona una descripción detallada del bot de trading automático desarrollado para operar en el mercado de criptomonedas a través de la API de Binance. El bot implementa una estrategia de Grid Trading Adaptativo con características avanzadas de gestión de riesgos, diseñado específicamente para realizar operaciones pequeñas y seguras que permitan un crecimiento diario constante.

## Estructura del Sistema

El sistema está compuesto por los siguientes componentes principales:

1. **Módulo de Configuración** (`config.py`): Almacena todos los parámetros configurables del sistema.
2. **Bot de Trading** (`grid_trading_bot.py`): Implementa la estrategia de Grid Trading Adaptativo.
3. **Gestor de Riesgos** (`risk_manager.py`): Proporciona capas adicionales de protección y ajuste dinámico de parámetros.
4. **Sistema de Trading Seguro** (`safe_trading_system.py`): Integra el bot y el gestor de riesgos en un sistema completo.
5. **Herramientas de Prueba** (`test_trading_system.py`): Permite probar el sistema en un entorno controlado.
6. **Analizador de Rendimiento** (`performance_analyzer.py`): Evalúa el rendimiento del bot y genera recomendaciones.

## Configuración del Sistema

### Requisitos Previos

- Python 3.6 o superior
- Cuenta en Binance (testnet para pruebas, cuenta real para operaciones reales)
- Claves API de Binance con permisos de lectura y trading

Añadir claves API en `config.py`

```bash
TESTNET_API_KEY = ""
TESTNET_API_SECRET = ""
```

### Instalación de Dependencias

```bash
pip install python-binance python-dotenv
```

### Archivo de Configuración

El archivo `config.py` contiene todos los parámetros configurables del sistema:

```python
# Configuración de la API de Binance (Testnet)
TESTNET_API_KEY = "tu_api_key"
TESTNET_API_SECRET = "tu_api_secret"

# Configuración del bot
TRADING_SYMBOL = "BTCUSDT"  # Par de trading predeterminado
INVESTMENT_AMOUNT = 100.0    # Cantidad en USDT para invertir por operación
TAKE_PROFIT_PERCENT = 1.0    # Porcentaje de beneficio objetivo (1%)
STOP_LOSS_PERCENT = 0.5      # Porcentaje de pérdida máxima permitida (0.5%)
MAX_TRADES_PER_DAY = 5       # Número máximo de operaciones por día
RISK_PERCENTAGE = 1.0        # Porcentaje del capital total a arriesgar por operación

# Configuración de la estrategia
STRATEGY_TYPE = "grid_trading"  # Tipo de estrategia: grid_trading, dca, etc.
GRID_LEVELS = 5                 # Número de niveles para grid trading
GRID_SPACING_PERCENT = 0.5      # Espaciado entre niveles en porcentaje

# Configuración de intervalos
CHECK_INTERVAL = 300  # Intervalo para verificar precios (en segundos)
```

## Estrategia de Grid Trading Adaptativo

### Concepto

La estrategia de Grid Trading Adaptativo establece una cuadrícula de órdenes de compra y venta a diferentes niveles de precio dentro de un rango predefinido. La cuadrícula se adapta automáticamente a la volatilidad del mercado, ajustando el espaciado entre niveles y el rango total.

### Características Principales

1. **Adaptabilidad del Rango**: El rango de la cuadrícula se ajusta periódicamente basado en la volatilidad reciente del mercado.
2. **Gestión de Riesgo Integrada**: Cada nivel tiene un stop loss dinámico para proteger contra movimientos extremos del mercado.
3. **Tamaño de Posición Variable**: El tamaño de las órdenes se ajusta según la distancia desde el precio medio, siendo más pequeñas en los extremos.
4. **Toma de Beneficios Escalonada**: Diferentes objetivos de beneficio para diferentes niveles de la cuadrícula.
5. **Análisis de Tendencia**: Incorpora un filtro simple de tendencia para ajustar el sesgo de la cuadrícula.

### Implementación

El bot calcula la cuadrícula de precios basándose en el precio actual y la volatilidad del mercado:

```python
def calculate_grid_prices(self):
    """Calcula los precios de la cuadrícula basados en el precio actual y la volatilidad"""
    current_price = self.get_current_price()
    if not current_price:
        return False
    
    # Obtener datos históricos para calcular la volatilidad
    klines = self.client.get_historical_klines(
        self.symbol, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC"
    )
    
    # Calcular la volatilidad (desviación estándar de los precios)
    prices = [float(kline[4]) for kline in klines]  # Precio de cierre
    avg_price = sum(prices) / len(prices)
    variance = sum([(p - avg_price) ** 2 for p in prices]) / len(prices)
    volatility = math.sqrt(variance) / avg_price * 100  # Volatilidad en porcentaje
    
    # Ajustar el espaciado de la cuadrícula según la volatilidad
    adjusted_spacing = max(self.grid_spacing_percent, volatility / 10)
    
    # Calcular el rango de la cuadrícula
    grid_range = 1.5 * (1 + volatility / 100)
    upper_limit = current_price * (1 + grid_range / 100)
    lower_limit = current_price * (1 - grid_range / 100)
    
    # Crear la cuadrícula de precios
    self.grid_prices = []
    for i in range(self.grid_levels):
        level_price = lower_limit + (upper_limit - lower_limit) * i / (self.grid_levels - 1)
        self.grid_prices.append(round(level_price, 2))
    
    return True
```

## Sistema de Gestión de Riesgos

### Características de Gestión de Riesgos

1. **Límite de Pérdida Diaria**: El sistema se pausa automáticamente si se alcanza un umbral de pérdida diaria.
2. **Monitoreo de Volatilidad**: Pausa las operaciones durante períodos de volatilidad extrema.
3. **Ajuste Dinámico de Parámetros**: Modifica los parámetros del bot basado en el rendimiento reciente.
4. **Reserva de Balance**: Mantiene una parte del capital como reserva de seguridad.
5. **Límite de Operaciones Diarias**: Controla el número máximo de operaciones por día.

### Cálculo de Métricas de Riesgo

El gestor de riesgos calcula diversas métricas para evaluar el rendimiento y ajustar los parámetros:

```python
def calculate_risk_metrics(self):
    """Calcula métricas de riesgo basadas en el historial de operaciones"""
    # Convertir historial a DataFrame para análisis
    df = pd.DataFrame(self.trades_history)
    
    # Calcular métricas
    win_rate = len(df[df['pnl'] > 0]) / len(df) * 100
    avg_profit = df[df['pnl'] > 0]['pnl'].mean()
    avg_loss = df[df['pnl'] < 0]['pnl'].mean()
    profit_factor = abs(df[df['pnl'] > 0]['pnl'].sum() / df[df['pnl'] < 0]['pnl'].sum())
    
    # Calcular drawdown
    cumulative = df['pnl'].cumsum()
    max_dd = 0
    peak = cumulative.iloc[0]
    
    for value in cumulative:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    # Guardar métricas
    self.risk_metrics = {
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd,
        'sharpe_ratio': self._calculate_sharpe_ratio(df['pnl']),
        'total_trades': len(df),
        'profitable_trades': len(df[df['pnl'] > 0]),
        'losing_trades': len(df[df['pnl'] < 0])
    }
    
    return self.risk_metrics
```

## Guía de Uso

### Configuración Inicial

1. Clonar el repositorio o descargar todos los archivos del sistema.
2. Instalar las dependencias requeridas:
   ```bash
   pip install python-binance python-dotenv
   ```
3. Editar el archivo `config.py` con tus claves API de Binance y parámetros deseados.

### Ejecución del Bot

Para ejecutar el bot en modo normal:

```bash
python safe_trading_system.py
```

Para ejecutar el bot en modo de prueba (duración limitada):

```bash
python test_trading_system.py
```

### Análisis de Rendimiento

Para analizar el rendimiento del bot después de un período de operación:

```bash
python performance_analyzer.py
```

Esto generará un informe detallado (`performance_report.md`) y gráficos de rendimiento en el directorio `performance_charts`.

## Recomendaciones de Optimización

Basado en el análisis de rendimiento, se recomiendan las siguientes optimizaciones:

1. **Ajustar el Espaciado de la Cuadrícula**: Reducir el espaciado para aumentar la frecuencia de operaciones rentables.
2. **Mejorar los Niveles de Take Profit**: Ajustar para mejorar la relación beneficio/pérdida.
3. **Implementar Stop Loss Más Estrictos**: Reducir el drawdown máximo.
4. **Mejorar la Consistencia de los Retornos**: Trabajar en estrategias para aumentar el Sharpe Ratio.

## Limitaciones y Consideraciones

1. **Entorno de Testnet vs. Producción**: El comportamiento en el entorno de testnet puede diferir del entorno de producción debido a diferencias en la liquidez y la latencia.
2. **Riesgo de Mercado**: Ninguna estrategia de trading puede garantizar beneficios. Utilice este bot con capital que esté dispuesto a arriesgar.
3. **Ajustes Necesarios**: Los parámetros óptimos pueden variar según las condiciones del mercado. Se recomienda revisar y ajustar periódicamente.
4. **Comisiones**: Las comisiones de trading pueden afectar significativamente la rentabilidad, especialmente en estrategias de alta frecuencia.

## Mantenimiento y Actualizaciones

Se recomienda realizar las siguientes tareas de mantenimiento:

1. **Actualización de Dependencias**: Mantener actualizadas las bibliotecas utilizadas.
2. **Revisión de Parámetros**: Ajustar los parámetros periódicamente basado en el análisis de rendimiento.
3. **Backup de Datos**: Realizar copias de seguridad regulares del historial de operaciones.
4. **Monitoreo de Cambios en la API**: Estar atento a cambios en la API de Binance que puedan afectar el funcionamiento del bot.

## TO-DO

1. Crear archivo de configuración del entorno
  - [x] Crear archivo para almacenar las claves API de forma segura
  - [x] Instalar las dependencias necesarias (python-binance, python-dotenv)


2. Probar la conexión con la API de Binance
  - [x] Verificar que las claves API funcionan correctamente
  - [x] Obtener información básica de la cuenta


3. Investigar estrategias seguras de trading
  - [x] Analizar estrategias de bajo riesgo para crecimiento diario
  - [x] Seleccionar la estrategia más adecuada para operaciones pequeñas
  - [x] Definir parámetros óptimos para la estrategia seleccionada


4. Implementar un bot de trading conservador
  - [x] Diseñar la lógica del bot con enfoque en seguridad
  - [x] Implementar funciones básicas de trading (precios, órdenes)
  - [x] Implementar la estrategia seleccionada


5. Añadir características de gestión de riesgos
  - [x] Implementar módulo de gestión de riesgos
  - [x] Integrar gestión de riesgos con el bot de trading
  - [x] Añadir ajuste dinámico de parámetros basado en rendimiento


6. Probar la funcionalidad del bot de trading
  - [x] Realizar pruebas con operaciones simuladas
  - [x] Verificar que el bot funciona según lo esperado


7. Analizar métricas de rendimiento
  - [x] Evaluar resultados de las pruebas
  - [x] Optimizar parámetros si es necesario


8. Documentar los detalles de implementación
  - [x] Crear documentación sobre la configuración
  - [x] Documentar las funciones implementadas
  - [x] Explicar la lógica del bot de trading


9. Presentar resultados al usuario
  - [x] Resumir el trabajo realizado
  - [x] Proporcionar instrucciones de uso

## Conclusión

El bot de trading automático con Grid Trading Adaptativo proporciona una solución para realizar operaciones pequeñas y seguras en el mercado de criptomonedas. Con su sistema avanzado de gestión de riesgos y capacidad de adaptación a las condiciones del mercado, ofrece una herramienta valiosa para traders que buscan un crecimiento constante con un perfil de riesgo controlado.

Las pruebas iniciales muestran áreas de mejora, y con las optimizaciones recomendadas, se espera que el rendimiento del bot mejore significativamente en el futuro.

## Licencia

<p align="center">
	Repositorio generado por <a href="https://github.com/sabiopobre" target="_blank">virtu 🎣</a>
</p>

<p align="center">
	<img src="https://open.soniditos.com/cat_footer.svg" />
</p>

<p align="center">
	Copyright &copy; 2025
</p>

<p align="center">
	<a href="/LICENSE"><img src="https://img.shields.io/static/v1.svg?style=for-the-badge&label=License&message=MIT&logoColor=d9e0ee&colorA=363a4f&colorB=b7bdf8"/></a>
</p>
