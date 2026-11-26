# openmediavault-qnapx39

Controlo das ventoinhas para QNAP antigos com Intel Atom e Super I/O
ITE IT8718F (TS-639 Pro e afins), em OpenMediaVault 7, incluindo i386.

Estes modelos não têm o controlador IT8528 usado pelo
[openmediavault-qnap](https://github.com/nader-eloshaiker/omv-qnap-plugin),
por isso aquele plugin não serve. Este usa o driver `it87` do kernel.

## O que faz (fase 1)

- Curva de ventoinha a partir da temperatura do CPU (`coretemp`), dos
  sensores da placa (`it87` temp1..3) e dos discos (S.M.A.R.T., sem acordar
  discos em repouso). A fonte mais quente manda.
- Histerese: sobe logo, só desce depois de arrefecer alguns graus.
- Segurança: sem leituras, um sensor 10 °C acima do máximo, ou o serviço
  parado ou com erro, as ventoinhas vão a 100 %.
- Aviso no registo se uma ventoinha marcar 0 RPM com potência alta.
- Página Sistema > QNAP (configuração e estado), indicadores no painel e
  gráficos em Diagnóstico > Estatísticas de desempenho.
- Carrega o `it87` no arranque.
- LEDs do painel (fase 3): Status verde fixo quando está tudo bem, vermelho
  com uma ventoinha avariada, um disco avariado (S.M.A.R.T. ou RAID) ou um
  RAID degradado; o LED vermelho da baía do disco avariado acende.

## TS-639 Pro (verificado)

| PWM | Ventoinha |
| --- | --- |
| pwm1 | fan1 |
| pwm2 | fan2 |
| pwm3 | não ligado |

O BIOS deixa as duas ventoinhas em modo manual a 50 %.

LEDs (pinos GPIO da IT8718F, Simple I/O em 0x0A20, todos ativos a 0):

| Pino | LED |
| --- | --- |
| GP23, GP22, GP21, GP20 | vermelho das baías 1, 2, 3, 4 |
| GP31, GP30 | vermelho das baías 5, 6 |
| GP35 | Status verde (o BIOS põe-no a piscar) |
| GP34 | Status vermelho |

O LED USB ainda não foi encontrado. `tools/it8718-gpio-dump.py` (só leitura)
e `tools/it8718-gpio-probe.py` ajudam a mapear outros modelos.

## Construir

```sh
make test
make deb          # em Debian 12 com build-essential debhelper fakeroot
make docker-deb   # ou com Docker, numa imagem i386/debian:bookworm
```

Instalar no NAS: `dpkg -i openmediavault-qnapx39_*_all.deb`, depois
Sistema > QNAP > Fan control, ativar, Guardar e Aplicar.

## Ainda por fazer

- Fase 2: ecrã LCD (A125 em `/dev/ttyS1`, 1200 baud) e os seus botões.
- LED USB e botões Reset/USB Copy (entradas GP16, GP17, GP24, GP25, GP40,
  GP53 por mapear).

## Licença

GPL-3.0-or-later. Partes adaptadas do openmediavault-qnap (Nader
Eloshaiker, GPL-3.0-or-later).
