"""Methodology page content, in Portuguese, for Angola users.

This page is written for a partner or a user who needs to decide
whether to trust a snapshot, not for a developer. It states what the
data are, what they are not, how they were collected, and how fresh
they are, in plain language. It makes no claim of state or operator
confirmation, and it promises no service level that does not exist.
"""

from dash import dcc, html

from map_dashboard.metodologia_content import source_status_lines


def build_source_status_items(meta):
    """Build a list of public source-status lines from a metadata dict."""
    return [html.Li(line) for line in source_status_lines(meta)]


def _section(title, children):
    return html.Section(
        [html.H2(title, className="metodologia__section-title")] + children,
        className="metodologia__section",
    )


def _para(text):
    return html.P(text, className="metodologia__copy")


def _bullets(items):
    return html.Ul(
        [html.Li(item, className="metodologia__copy") for item in items],
        className="metodologia__list",
    )


def build_metodologia_layout():
    return html.Div(
        [
            dcc.Interval(id="metodologia-refresh", interval=300 * 1000, n_intervals=0),
            html.Div("Metodologia", className="metodologia__eyebrow"),
            html.H1("Como recolhemos, tratamos e datamos os dados", className="metodologia__title"),
            _para(
                "Esta página explica, em linguagem simples, de onde vêm os dados "
                "do Angola Fuel Station Explorer, o que significam, o que não significam, "
                "e como saber se um snapshot ainda é recente. Se uma frase aqui não for "
                "clara, trate-a como um limite do projeto, não como uma garantia."
            ),
            html.Div(id="metodologia-meta", className="metodologia__snapshot"),
            html.Div(id="metodologia-source-status", className="metodologia__snapshot"),
            _section(
                "O que o projeto é",
                [
                    _para(
                        "O projeto é uma base de descoberta de postos de combustível em Angola, "
                        "pesquisável por operador, província, município ou nome. Cada registo "
                        "identifica um posto e a sua localização aproximada, na data da fonte "
                        "indicada, e pode ser citado através da data do snapshot."
                    ),
                    _para(
                        "O projeto é também um registo transparente: mostra a origem de cada "
                        "fonte, a data de geração do snapshot, o número de registos e de registos "
                        "rejeitados, e o estado de frescura. A transparência sobre limites faz "
                        "parte do produto, e não é um detalhe."
                    ),
                ],
            ),
            _section(
                "O que o projeto não é",
                [
                    _para(
                        "O projeto não é um registo estatal, não substitui nenhuma lista de "
                        "operadores, e nenhuma entidade pública ou operador confirmou estes dados "
                        "para este projeto. Não é uma lista completa nem exaustiva de todos os "
                        "postos de Angola. A cobertura é parcial, e as lacunas fazem parte da "
                        "informação."
                    ),
                    _para(
                        "O projeto não diz se um posto está aberto neste momento, se tem "
                        "combustível, qual é o preço, ou se está licenciado. Não é uma ferramenta "
                        "de operação em tempo real, e não deve ser usado como única base para "
                        "decisões críticas, como enviar uma frota ou planear uma rota crítica, "
                        "sem confirmação no local ou junto do operador."
                    ),
                ],
            ),
            _section(
                "De onde vêm os dados",
                [
                    _para(
                        "A base de partida é o OpenStreetMap, com registos de postos de combustível "
                        "em Angola. A essa base juntam-se listagens públicas de operadores, quando "
                        "disponíveis, e filtros por marca aplicados aos registos públicos. A lista "
                        "de fontes e o estado de cada fonte em cada snapshot estão no início desta "
                        "página e em /api/v1/meta."
                    ),
                    _para(
                        "Não foi identificada nenhuma API pública de postos de combustível em Angola, "
                        "de entidades públicas ou de operadores, que possa ser usada como fonte "
                        "principal. Por isso, a recolha depende de fontes públicas e da sua "
                        "disponibilidade em cada semana."
                    ),
                ],
            ),
            _section(
                "Política de qualidade do dado",
                [
                    _para(
                        "Um registo só entra no mapa se passar na validação: nome presente, operador "
                        "presente, coordenadas válidas e dentro de Angola, sem coordenadas (0, 0) e "
                        "sem artefactos de texto. O que falha vai para os registos rejeitados e nunca "
                        "aparece no mapa. Passar na validação significa que o registo pode ser usado "
                        "para descoberta de localização, e não que o posto está aberto ou a funcionar."
                    ),
                    html.H3("Dado confiável", className="metodologia__subtitle"),
                    _para(
                        "Um dado é considerado confiável para descoberta quando passou na validação, "
                        "tem fonte identificada, não está marcado como desatualizado, e pertence a um "
                        "snapshot com menos de 14 dias. Mesmo assim, só diz respeito à identidade e "
                        "à localização do posto na data da fonte, e não ao seu estado atual."
                    ),
                    html.H3("Dado incompleto", className="metodologia__subtitle"),
                    _para("Sinais de um registo incompleto:"),
                    _bullets(
                        [
                            "morada em falta, ou morada apenas com plus code;",
                            "província inferida a partir do município;",
                            "município em falta, ou preenchido por regra de recurso a partir da província;",
                            "nome genérico, igual ao nome do operador.",
                        ]
                    ),
                    _para("Um registo incompleto serve como ponto de partida, e não como ficha completa."),
                    html.H3("Dado potencialmente desatualizado", className="metodologia__subtitle"),
                    _para("Sinais de um registo potencialmente desatualizado:"),
                    _bullets(
                        [
                            "o registo está marcado como desatualizado;",
                            "a sua fonte falhou ou foi reutilizada na última geração;",
                            "o snapshot completo tem mais de 14 dias;",
                            "a página pública da fonte mudou ou deixou de responder.",
                        ]
                    ),
                    _para(
                        "Registos desatualizados não são apagados sem evidência. Ficam visíveis e "
                        "marcados, até serem confirmados ou corrigidos numa versão posterior."
                    ),
                    html.H3("Níveis de qualidade por fonte", className="metodologia__subtitle"),
                    _para(
                        "A qualidade depende da fonte. A tabela abaixo diz como interpretar cada nível. "
                        "Os níveis são agregados: se a maioria dos registos for de base pública, a "
                        "metodologia deve mostrar isso, e não diluir o nível mais baixo."
                    ),
                    html.Table(
                        [
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Nível"),
                                        html.Th("O que significa"),
                                        html.Th("Como usar"),
                                    ]
                                )
                            ),
                            html.Tbody(
                                [
                                    html.Tr(
                                        [
                                            html.Td("base_publica_osm"),
                                            html.Td(
                                                "Informação pública útil para descoberta, "
                                                "sem confirmação do operador."
                                            ),
                                            html.Td("Apenas para descoberta. Confirmar antes de decidir."),
                                        ]
                                    ),
                                    html.Tr(
                                        [
                                            html.Td("operador_via_osm"),
                                            html.Td(
                                                "Registo público filtrado pela marca do operador. "
                                                "Qualidade superior à base pública, mas ainda sem "
                                                "confirmação direta."
                                            ),
                                            html.Td("Para descoberta com mais confiança, ainda sem confirmação direta."),
                                        ]
                                    ),
                                    html.Tr(
                                        [
                                            html.Td("confirmado_pelo_operador"),
                                            html.Td(
                                                "Registo encontrado numa listagem pública do operador, "
                                                "na data indicada. É o nível mais alto neste projeto."
                                            ),
                                            html.Td(
                                                "Para descoberta. Não prova que o posto está aberto, "
                                                "tem combustível, está licenciado, ou que o operador "
                                                "apoia este projeto."
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                        ],
                        className="metodologia__table",
                    ),
                    _para(
                        "Em fase 0, confirmado_pelo_operador significa apenas que o registo foi "
                        "encontrado numa listagem pública do operador. Não significa que o operador "
                        "forneceu os dados ao abrigo de um acordo, nem que confirmou os dados para "
                        "este projeto. Um nível com fornecimento direto por acordo só poderá ser usado "
                        "com um acordo escrito com o operador, e até lá esse rótulo não existe no dataset."
                    ),
                ],
            ),
            _section(
                "Como tratamos registos duplicados",
                [
                    _para(
                        "Dois registos são considerados o mesmo posto quando têm o mesmo operador, o "
                        "mesmo nome normalizado, e coordenadas arredondadas a 4 casas decimais. "
                        "Quando há duplicados, a ordem de preferência é: registo recente em vez de "
                        "registo desatualizado; listagem pública do operador em vez de OpenStreetMap; "
                        "registo filtrado por marca em vez de registo geral; registo com morada em vez "
                        "de registo sem morada."
                    ),
                ],
            ),
            _section(
                "O que os dados representam, e o que não representam",
                [
                    _para(
                        "Os dados representam a identidade e a localização aproximada de postos de "
                        "combustível em Angola encontrados em fontes públicas identificadas, na data "
                        "do snapshot. São uma base de descoberta, pesquisável e citável."
                    ),
                    _para(
                        "Os dados não representam o estado atual de funcionamento de um posto, a "
                        "disponibilidade de combustível, os preços, o licenciamento, nem uma lista "
                        "completa de todos os postos do país."
                    ),
                    _para(
                        "Quando a fonte é de baixa confiança, ou quando o registo está marcado como "
                        "desatualizado, trate o dado apenas como um indicador aproximado, para "
                        "descoberta. Confirme no local ou junto do operador antes de qualquer decisão "
                        "operacional."
                    ),
                    _para(
                        "Quando a morada é apenas um plus code, a província foi inferida, o município "
                        "veio por regra de recurso, ou o nome é genérico e igual ao operador, o registo "
                        "é apenas aproximado, mesmo que apareça no mapa com coordenadas."
                    ),
                ],
            ),
            _section(
                "Frescura e atualização",
                [
                    _para(
                        "A única data de atualização do dataset é a data de geração do snapshot, "
                        "generated_at, em /api/v1/meta e no selo junto aos contadores no mapa. Não é "
                        "a data de publicação do site, nem o tempo de cache de 300 segundos."
                    ),
                    _para(
                        "O limiar de frescura é de 14 dias, porque a recolha é semanal e precisa de "
                        "margem. Até 14 dias, o snapshot é considerado recente. Entre 15 e 28 dias, "
                        "é considerado desatualizado, com aviso visível junto ao mapa. Acima de 28 dias, "
                        "é considerado em atraso, com aviso visível e uma nota datada da responsável "
                        "nesta página."
                    ),
                    _para(
                        "Se a data de geração estiver em falta, for inválida, ou estiver no futuro, "
                        "o site e a API mostram a data como indisponível. Nunca é inventada uma data."
                    ),
                    _para(
                        "Para citar um snapshot, cite sempre a data de geração e o identificador da "
                        "versão, que nesta fase é igual à data de geração, e não apenas o nome do site. "
                        "Se o snapshot tiver mais de 14 dias, trate-o como histórico, e não como atual."
                    ),
                ],
            ),
            _section(
                "Governança do refresh",
                [
                    _para(
                        "Responsável pelo dataset: Helena Pedro, única responsável. A responsável "
                        "aciona recolhas manuais, revê falhas da automação, tria correções, aprova "
                        "publicações e publica notas datadas de atraso."
                    ),
                    _para(
                        "Cadência prevista: recolha semanal automática, às segundas-feiras, às 06:00 "
                        "UTC, através de GitHub Actions. A cadência é um objetivo público, e não uma "
                        "garantia contratual de publicação todas as segundas-feiras."
                    ),
                    _para(
                        "Antes de uma nova versão ser publicada, tem de passar no portão de publicação: "
                        "testes aprovados, ficheiro JSON válido, data de geração presente e sem data no "
                        "futuro, e número de registos superior a zero. Se o portão falhar, não há nova "
                        "versão, e o snapshot anterior continua em produção, com a idade a crescer e o "
                        "aviso a aparecer automaticamente depois de 14 dias."
                    ),
                    _para(
                        "Quando uma única fonte falha, os registos anteriores dessa fonte são reutilizados "
                        "e marcados como desatualizados, e a falha fica visível em /api/v1/meta e nesta "
                        "página. Quando a recolha falha no conjunto, ou um teste falha, não há novo "
                        "snapshot. A falha fica no registo da automação, e nesta fase não há outro canal "
                        "de alerta: o próprio selo de frescura é o controlo, e não pode ser suprimido."
                    ),
                    _para(
                        "Prazos públicos, que não são um acordo de nível de serviço: a responsável revê "
                        "uma falha da automação no prazo de 7 dias de calendário, ou na próxima recolha "
                        "prevista, consoante o que acontecer primeiro, e regista a decisão, que pode ser "
                        "voltar a correr, corrigir o adaptador, ou deixar o aviso visível. Correções "
                        "aceites entram apenas no próximo snapshot publicado, e nunca são editadas no "
                        "snapshot atual. Se a idade passar os 28 dias, esta página tem de mostrar uma "
                        "nota datada com a causa conhecida e o próximo passo, ou uma nota de pausa da "
                        "cadência semanal. Um aviso a crescer em silêncio não é aceitável."
                    ),
                    _para(
                        "Não há, nesta fase, uma pessoa de recurso formal, nem suporte 24 horas, nem "
                        "garantia de disponibilidade do serviço, que corre num único dyno. A governança "
                        "tem de ser revista antes de qualquer compromisso com um parceiro que pague."
                    ),
                ],
            ),
            _section(
                "Como reportar um erro",
                [
                    _para(
                        "O caminho principal para reportar um erro é um formulário sem conta: não é "
                        "preciso ter conta GitHub, nem criar uma, para reportar. O formulário ainda "
                        "não está publicado nesta página; quando estiver, o link fica aqui, com os "
                        "mesmos campos: identificador do posto, data do snapshot usado, tipo de "
                        "problema e, se possível, uma fonte pública. Não é pedido nome, email, "
                        "telefone ou localização do utilizador."
                    ),
                    _para(
                        "Quem já tiver conta GitHub pode, em alternativa, abrir uma issue pública no "
                        "repositório do projeto, com os mesmos campos. A issue é o caminho secundário, "
                        "e não o único."
                    ),
                    html.A(
                        "Abrir uma issue no repositório público",
                        href="https://github.com/helenapedro/Angola-Fuel-Station-Explorer/issues/new",
                        target="_blank",
                        className="metodologia__link",
                    ),
                    _para(
                        "Uma correção aceite aparece apenas numa versão posterior, e nunca é editada "
                        "no snapshot atual, para que cada versão continue a poder ser citada e verificada."
                    ),
                ],
            ),
            html.Div(
                html.A("Voltar ao mapa", href="/", className="metodologia__link"),
                className="metodologia__back",
            ),
        ],
        className="metodologia",
    )
