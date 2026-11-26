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
  RAID degradado; o LED vermelho da baía do disco avariado acende; o LED
  USB fica azul enquanto houver um disco USB ligado.
- Ecrã LCD da frente (fase 2): IP de cada placa de rede, estado,
  temperaturas, ventoinhas, cada baía (disco, temperatura, estado,
  tamanho, modelo), cada RAID (estado, reconstrução), cada volume (uso,
  espaço livre) e tempo ligado. SELECT mostra a página seguinte e
  ENTER a anterior. Na última página, ENTER abre o menu Reiniciar/Desligar
  (pede confirmação; pode ser desativado). A luz apaga ao fim de um tempo sem carregar num botão
  (0 = sempre acesa) e volta a acender com um problema novo.

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
| GP35 | Status verde |
| GP34 | Status vermelho |
| GP50 | USB (azul) |

O BIOS faz piscar o Status com o gerador de pisca 1 ligado ao GP26 (código
0x16). O plugin desliga esse pisca e o Status fica fixo; volta a piscar
quando o serviço para.

Baías (nomes de `/dev/disk/by-path`, verificado pelos números de série):

| Baía | Porta SATA |
| --- | --- |
| 1 | `pci-0000:00:1f.1-ata-1` (chipset) |
| 2, 3, 4 | `pci-0000:03:00.0-ata-2`, `-ata-3`, `-ata-4` |
| 5, 6 | `pci-0000:04:00.0-ata-1`, `-ata-2` |

A porta 1 da `03:00.0` não é uma baía. Os números `ataN` do kernel mudam
entre arranques e não servem para identificar uma baía.

LCD: A125 (2 linhas de 16) em `/dev/ttyS1`, 1200 baud 8N1, ligado pelo
GP10 (ativo a 0; o BIOS deixa-o a 1 e o ecrã apagado). Comandos:
`4D 5E 01`/`00` acende/apaga a luz, `4D 0C <linha> 10` + 16 caracteres (10 = comprimento)
escreve uma linha. Os botões enviam `53 05 00 01` (ENTER), `53 05 00 02`
(SELECT) e `53 05 00 00` (largar). Nenhum outro programa pode ter a
`/dev/ttyS1` aberta, senão o ecrã pisca.

`tools/it8718-gpio-dump.py` (só leitura)
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

- Botões Reset/USB Copy (entradas GP16, GP17, GP24, GP25, GP40,
  GP53 por mapear).

## Licença

GPL-3.0-or-later. Partes adaptadas do openmediavault-qnap (Nader
Eloshaiker, GPL-3.0-or-later).
