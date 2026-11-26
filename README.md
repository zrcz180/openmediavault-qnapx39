# openmediavault-qnapx39

Plugin para o [OpenMediaVault](https://www.openmediavault.org/) 7 que põe
a funcionar o hardware da frente e as ventoinhas dos QNAP antigos com
Intel Atom e Super I/O ITE IT8718F (série TS-x39, como o TS-639 Pro),
incluindo instalações **i386** (32 bits).

> **Baseado no [omv-qnap-plugin](https://github.com/nader-eloshaiker/omv-qnap-plugin)**
> de Nader Eloshaiker (GPL-3.0-or-later). Este projeto é um derivado
> (fork) desse plugin, adaptado ao OpenMediaVault 7 i386 e ao hardware da
> série TS-x39.

O plugin original foi feito para os QNAP com o controlador IT8528 e para
o OpenMediaVault 8 (amd64/arm64). Estes modelos não têm esse controlador,
por isso aqui o acesso ao hardware foi refeito: usa o driver `it87` do
kernel, os pinos GPIO da IT8718F e a porta série do ecrã. Do original
vêm a estrutura do plugin (Salt, páginas da interface, painel, gráficos),
o leitor de temperaturas dos discos e os emails de avaria.

Versão atual: **7.3.0** (OpenMediaVault 7, Debian 12 "bookworm").

## O que está incorporado

### Ventoinhas

- Curva automática a partir da temperatura do CPU (`coretemp`), dos
  sensores da placa (`it87` temp1..3) e dos discos (S.M.A.R.T.). A fonte
  mais quente decide a velocidade.
- Os discos em repouso nunca são acordados para ler a temperatura.
- Histerese: a velocidade sobe logo e só desce depois de arrefecer alguns
  graus.
- Modo manual com velocidade fixa.
- Segurança: sem leituras, com um sensor 10 °C acima do máximo, ou com o
  serviço parado ou com erro, as ventoinhas vão a 100 %.
- Aviso no registo se uma ventoinha marcar 0 RPM com potência alta.
- Carrega o módulo `it87` no arranque.

### LEDs do painel

- **Status** verde fixo quando está tudo bem (o BIOS deixa-o a piscar).
- **Status** vermelho com uma ventoinha avariada, um disco avariado
  (S.M.A.R.T. ou RAID) ou um RAID degradado.
- **LED vermelho da baía** do disco avariado.
- **USB** azul enquanto houver um disco USB ligado.
- Quando o serviço para, os LEDs voltam ao estado em que o BIOS os deixou.

### Ecrã LCD da frente

Páginas (SELECT mostra a seguinte, ENTER a anterior):

| Página | Exemplo |
| --- | --- |
| Uma por placa de rede | `nas eth0 1000Mb` / `192.168.1.5` |
| Estado | `Status: OK` / `All well`, ou o problema |
| Temperaturas | `CPU 45C` / `System 40C` |
| Ventoinhas | `Fans 30%` / `1715 1713 RPM` |
| Discos (resumo) | `Disks 6, max 38C` / `min 33C` |
| Uma por baía | `B1 sda 35C OK` / `2.0T WDC WD20EFRX` |
| Uma por RAID | `md0 raid5 6/6` / `OK [UUUUUU]` |
| Uma por volume | `dados 78%` / `1.2T free/9.8T` |
| Tempo ligado | `Up 3d 04:12` / `Load 0.15 0.20 0.18` |
| Desligar/Reiniciar | `Shutdown/Reboot` / `ENTER = menu` |

- A luz apaga ao fim de um tempo sem carregar num botão (60 s por
  omissão; 0 = sempre acesa) e volta a acender com um problema novo, que
  salta logo para a página de estado.
- Os discos de cada baía aparecem com o estado OK, FAIL, sleep (em
  repouso) ou empty (baía vazia).
- O RAID mostra DEGRADED quando falta um disco e a percentagem durante uma
  reconstrução.
- Menu Reiniciar/Desligar: na última página, ENTER abre o menu, SELECT
  escolhe e ENTER confirma; é preciso um segundo ENTER em "Sure?". SELECT,
  ou 15 s sem carregar, cancela. Pode ser desativado.

### Interface web e avisos

- **Sistema > QNAP > Fan control**: ventoinhas, temperaturas, LEDs, mapa
  das baías e ecrã LCD.
- **Sistema > QNAP > Status**: leituras atuais e estado do LED.
- **Sistema > QNAP > Disks**: cada baía com o disco, modelo, tamanho,
  temperatura, estado e LED vermelho.
- Painel inicial: quadro com as ventoinhas e temperaturas, dados do
  equipamento, gráficos do último dia e indicadores redondos (CPU,
  sistema, discos, potência das ventoinhas).
- Gráficos em Diagnóstico > Estatísticas de desempenho (hora, dia,
  semana, mês e ano).
- **Emails de avaria** pelas notificações do OMV: ventoinha parada,
  temperatura crítica (10 °C acima do máximo), disco avariado, RAID
  degradado ou volume cheio (95 %) durante mais de 1 minuto, quando o
  problema passa, e quando o serviço para sem ser pedido. Para ligar:
  Sistema > Notificação > Definições com o email configurado, e em
  Eventos marcar "QNAP TS-x39 hardware" e Guardar. Uma temperatura
  crítica ou um volume cheio também põem o Status vermelho.

## Instalar

1. Descarregar o `openmediavault-qnapx39_7.3.0_all.deb` da página
   [Releases](https://github.com/zrcz180/openmediavault-qnapx39/releases)
   (ou construí-lo, ver abaixo).
2. Se tinha outro programa a usar o ecrã (por exemplo um serviço
   `qnap-lcd` próprio), desativá-lo, senão o ecrã pisca:
   ```sh
   sudo systemctl disable --now qnap-lcd
   ```
3. Instalar:
   ```sh
   sudo dpkg -i openmediavault-qnapx39_7.3.0_all.deb
   ```
4. Em Sistema > QNAP > Fan control, ativar, **Guardar** e **Aplicar**.

O serviço chama-se `qnapx39d`. Ver o estado com
`sudo /usr/sbin/qnapx39d status` e o registo com `journalctl -u qnapx39d`.

## Hardware verificado: TS-639 Pro

Atom N270 (32 bits), IT8718F, OpenMediaVault 7 i386.

**Ventoinhas**: `pwm1` controla `fan1`, `pwm2` controla `fan2`, `pwm3`
não está ligado. O BIOS deixa as duas em modo manual a 50 %.

**LEDs** (pinos GPIO da IT8718F, Simple I/O em 0x0A20, todos ativos a 0):

| Pino | LED |
| --- | --- |
| GP23, GP22, GP21, GP20 | vermelho das baías 1, 2, 3, 4 |
| GP31, GP30 | vermelho das baías 5, 6 |
| GP35 | Status verde |
| GP34 | Status vermelho |
| GP50 | USB (azul) |

O BIOS faz piscar o Status com o gerador de pisca 1 ligado ao GP26
(código 0x16). O plugin desliga esse pisca e o Status fica fixo.

**Baías** (nomes de `/dev/disk/by-path`, verificados pelos números de
série):

| Baía | Porta SATA |
| --- | --- |
| 1 | `pci-0000:00:1f.1-ata-1` (chipset) |
| 2, 3, 4 | `pci-0000:03:00.0-ata-2`, `-ata-3`, `-ata-4` |
| 5, 6 | `pci-0000:04:00.0-ata-1`, `-ata-2` |

A porta 1 da `03:00.0` fica dentro da caixa e não é uma baía. Os números
`ataN` do kernel e as letras `sdX` mudam entre arranques e não servem para
identificar uma baía.

**LCD**: A125, 2 linhas de 16 caracteres, em `/dev/ttyS1` a 1200 baud 8N1,
ligado pelo GP10 (ativo a 0; o BIOS deixa-o a 1 e o ecrã apagado).

| Bytes | Significado |
| --- | --- |
| `4D 5E 01` / `4D 5E 00` | acende / apaga a luz |
| `4D 0C <linha> 10` + 16 caracteres | escreve a linha 0 ou 1 (`10` = comprimento) |
| `53 05 00 01` | botão ENTER (enviado pelo ecrã) |
| `53 05 00 02` | botão SELECT |
| `53 05 00 00` | botão largado |

Nenhum outro programa pode ter a `/dev/ttyS1` aberta.

Para outros modelos da série, `tools/it8718-gpio-dump.py` (só leitura) e
`tools/it8718-gpio-probe.py` ajudam a mapear os LEDs, e o mapa das baías
pode ser mudado na interface.

## Construir

```sh
make test         # testes unitários
make deb          # em Debian 12 com build-essential debhelper fakeroot
make docker-deb   # ou com Docker, numa imagem i386/debian:bookworm
```

O GitHub Actions corre os testes e constrói o .deb em cada push.

## Ainda por fazer

- Botões Reset e USB Copy (entradas GP16, GP17, GP24, GP25, GP40 e GP53
  ainda por mapear).

## Licença

GPL-3.0-or-later, a mesma licença do original.

Baseado no [omv-qnap-plugin](https://github.com/nader-eloshaiker/omv-qnap-plugin)
© Nader Eloshaiker, GPL-3.0-or-later. O leitor de temperaturas dos discos
e os emails de avaria foram adaptados desse projeto.
