(function () {
  const fieldEditor = document.getElementById("field-editor");
  const addFieldButton = document.getElementById("add-field-button");
  const fieldTemplate = document.getElementById("field-row-template");

  if (fieldEditor && addFieldButton && fieldTemplate) {
    function nextOrder() {
      return fieldEditor.querySelectorAll(".field-row").length + 1;
    }

    function bindRemove(button) {
      button.addEventListener("click", () => {
        button.closest(".field-row").remove();
      });
    }

    fieldEditor.querySelectorAll(".remove-field-button").forEach(bindRemove);

    addFieldButton.addEventListener("click", () => {
      const fragment = fieldTemplate.content.cloneNode(true);
      const ordem = fragment.querySelector("input[name='field_ordem']");
      if (ordem) {
        ordem.value = nextOrder();
      }
      fragment.querySelectorAll(".remove-field-button").forEach(bindRemove);
      fieldEditor.appendChild(fragment);
    });
  }
})();

(function () {
  const attributeEditor = document.getElementById("attribute-editor");
  const addAttributeButton = document.getElementById("add-attribute-button");
  const attributeTemplate = document.getElementById("attribute-row-template");

  if (!attributeEditor || !addAttributeButton || !attributeTemplate) return;

  function slug(value) {
    return (value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || "atributo";
  }

  function rows() {
    return Array.from(attributeEditor.querySelectorAll("[data-attribute-row]"));
  }

  function reindex() {
    rows().forEach((row, index) => {
      const ordem = row.querySelector("input[name='attr_ordem']");
      const obrigatorio = row.querySelector("input[name='attr_obrigatorio']");
      const resumo = row.querySelector("input[name='attr_visivel_resumo']");
      const title = row.querySelector(".atributo-card-header strong");
      if (title) {
        title.textContent = `Atributo tecnico #${index + 1}`;
      }
      if (ordem && !ordem.value) {
        ordem.value = index + 1;
      }
      if (obrigatorio) {
        obrigatorio.value = String(index);
      }
      if (resumo) {
        resumo.value = String(index);
      }
    });
  }

  function bindRow(row) {
    const nome = row.querySelector("input[name='attr_nome']");
    const chave = row.querySelector("input[name='attr_chave']");
    const remove = row.querySelector(".remove-attribute-button");

    if (nome && chave) {
      nome.addEventListener("input", () => {
        if (!chave.dataset.edited) {
          chave.value = slug(nome.value);
        }
      });
      chave.addEventListener("input", () => {
        chave.dataset.edited = "true";
        chave.value = slug(chave.value);
      });
    }

    if (remove) {
      remove.addEventListener("click", () => {
        row.remove();
        reindex();
      });
    }
  }

  rows().forEach(bindRow);
  reindex();

  addAttributeButton.addEventListener("click", () => {
    const fragment = attributeTemplate.content.cloneNode(true);
    const row = fragment.querySelector("[data-attribute-row]");
    attributeEditor.appendChild(fragment);
    bindRow(row);
    reindex();
  });
})();

(function () {
  const optionEditor = document.getElementById("option-editor");
  const addOptionButton = document.getElementById("add-option-button");
  const optionTemplate = document.getElementById("option-row-template");

  if (!optionEditor || !addOptionButton || !optionTemplate) return;

  function slug(value) {
    return (value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || "opcao";
  }

  function rows() {
    return Array.from(optionEditor.querySelectorAll("[data-option-row]"));
  }

  function reindex() {
    rows().forEach((row, index) => {
      const title = row.querySelector(".atributo-card-header strong");
      const ordem = row.querySelector("input[name='op_ordem']");
      const obrigatorio = row.querySelector("input[name='op_obrigatorio']");
      const ativo = row.querySelector("input[name='op_ativo']");
      if (title) title.textContent = `Acessorio/opcional #${index + 1}`;
      if (ordem && !ordem.value) ordem.value = index + 1;
      if (obrigatorio) obrigatorio.value = String(index);
      if (ativo) ativo.value = String(index);
    });
  }

  function bindRow(row) {
    const nome = row.querySelector("input[name='op_nome']");
    const chave = row.querySelector("input[name='op_chave']");
    const dependeChave = row.querySelector("input[name='op_depende_chave']");
    const remove = row.querySelector(".remove-option-button");

    if (nome && chave) {
      nome.addEventListener("input", () => {
        if (!chave.dataset.edited) chave.value = slug(nome.value);
      });
      chave.addEventListener("input", () => {
        chave.dataset.edited = "true";
        chave.value = slug(chave.value);
      });
    }
    if (dependeChave) {
      dependeChave.addEventListener("input", () => {
        dependeChave.value = slug(dependeChave.value);
      });
    }
    if (remove) {
      remove.addEventListener("click", () => {
        row.remove();
        reindex();
      });
    }
  }

  rows().forEach(bindRow);
  reindex();

  addOptionButton.addEventListener("click", () => {
    const fragment = optionTemplate.content.cloneNode(true);
    const row = fragment.querySelector("[data-option-row]");
    optionEditor.appendChild(fragment);
    bindRow(row);
    reindex();
  });
})();

(function () {
  const tipoObraSelect = document.getElementById("tipo-obra");

  function currentTipoObra() {
    return tipoObraSelect ? tipoObraSelect.value : window.ANTEPROJETO_TIPO_OBRA;
  }

  function situacaoOptions() {
    if (currentTipoObra() === "Obra nova") {
      return ["Novo"];
    }
    return ["Novo", "Existente", "Substituir", "Adequar", "Remover"];
  }

  function renderSituacao(select) {
    const atual = select.dataset.current || "";
    select.innerHTML = "";

    situacaoOptions().forEach((opcao) => {
      const option = document.createElement("option");
      option.value = opcao;
      option.textContent = opcao;
      option.selected = (atual && atual === opcao) || (!atual && opcao === "Novo");
      select.appendChild(option);
    });
  }

  document.querySelectorAll(".situacao-select").forEach(renderSituacao);

  if (tipoObraSelect) {
    tipoObraSelect.addEventListener("change", () => {
      document.querySelectorAll(".situacao-select").forEach((select) => {
        select.dataset.current = "";
        renderSituacao(select);
      });
    });
  }
})();

(function () {
  const form = document.getElementById("cascade-equipment-form");
  if (!form) return;

  const selects = [
    document.getElementById("equipamento-nivel-0"),
    document.getElementById("equipamento-nivel-1"),
    document.getElementById("equipamento-nivel-2"),
  ];
  const finalInput = document.getElementById("equipamento-final-id");
  const pathBox = document.getElementById("equipamento-caminho-selecionado");
  const attrsBox = document.getElementById("equipamento-atributos-carregados");
  const optionsBox = document.getElementById("equipamento-opcoes-carregadas");
  const variationLabels = Array.from(form.querySelectorAll("[data-variation-level]"));
  const finalFields = Array.from(form.querySelectorAll("[data-final-fields]"));
  const quantidadeInput = form.querySelector("[data-quantidade-input]");
  const selectedChain = window.ITEM_EDITANDO_CADEIA || [];
  const selectedOptions = window.ITEM_EDITANDO_OPCOES || {};
  const selectedCampos = window.ITEM_EDITANDO_CAMPOS || {};

  const transportadorConfig = {
    tipos: [
      { value: "redler", label: "Redler", subtipos: [{ value: "convencional", label: "Convencional" }, { value: "reversivel", label: "Reversivel" }] },
      { value: "correia", label: "Correia", subtipos: [{ value: "enclausurada", label: "Enclausurada" }, { value: "aberta", label: "Aberta" }, { value: "aberta_nova", label: "Aberta Nova" }] },
      { value: "hi_flight", label: "Hi-Flight", subtipos: [] },
      { value: "helicoidal", label: "Helicoidal", subtipos: [] },
      { value: "elevador", label: "Elevador", subtipos: [] },
    ],
    itens: {
      redler: ["sensor_rotacao", "sensor_temperatura", "sensor_embuchamento"],
      correia: ["sensor_rotacao", "sensor_temperatura", "sensor_embuchamento", "sensor_desalinhamento", "janela_alivio_pressao", "filtro_pontual"],
      hi_flight: ["sensor_rotacao", "sensor_temperatura", "sensor_embuchamento"],
      helicoidal: [],
      elevador: [
        "sensor_rotacao",
        "sensor_temperatura",
        "sensor_embuchamento",
        "sensor_desalinhamento",
        "modulo_alivio_pressao",
        "pe_auto_limpante",
        "plataforma_valvula_2_vias",
      ],
    },
    detalhes: {
      sensor_rotacao: { label: "Sensor de Rotação", categoria: "sensor" },
      sensor_temperatura: { label: "Sensor de Temperatura", categoria: "sensor" },
      sensor_embuchamento: { label: "Sensor de Embuchamento", categoria: "sensor" },
      sensor_desalinhamento: { label: "Sensor de Desalinhamento", categoria: "sensor" },
      janela_alivio_pressao: { label: "Janela de Alívio de Pressão", categoria: "acessorio" },
      filtro_pontual: { label: "Filtro Pontual", categoria: "acessorio" },
      modulo_alivio_pressao: { label: "Módulo de Alívio de Pressão", categoria: "acessorio" },
      pe_auto_limpante: { label: "Pé Auto-Limpante", categoria: "acessorio" },
      plataforma_valvula_2_vias: { label: "Plataforma p/ manutenção de válvula 2 vias", categoria: "acessorio" },
    },
  };

  const maquinaLimpezaConfig = {
    tipos: [
      { value: "pre_limpeza", label: "Pré-Limpeza" },
      { value: "pos_limpeza", label: "Pós-Limpeza" },
    ],
    modelos: {
      pre_limpeza: [
        { value: "mle_45_60", label: "MLE 45 - 60 t/h" },
        { value: "mle_95_120", label: "MLE 95 - 120 t/h" },
        { value: "mle_145_180", label: "MLE 145 - 180 t/h" },
        { value: "mle_190_240", label: "MLE 190 - 240 t/h" },
      ],
      pos_limpeza: [
        { value: "mle_45_47", label: "MLE 45 - 47 t/h" },
        { value: "mle_95_96", label: "MLE 95 - 96 t/h" },
        { value: "mle_145_144", label: "MLE 145 - 144 t/h" },
        { value: "mle_190_192", label: "MLE 190 - 192 t/h" },
      ],
    },
  };

  const secadorConfig = {
    modelos: [
      { value: "scc_202_22", label: "SCC-202 - 22 t/h" },
      { value: "scc_302_33", label: "SCC-302 - 33 t/h" },
      { value: "scc_303_49", label: "SCC-303 - 49 t/h" },
      { value: "scc_304_66", label: "SCC-304 - 66 t/h" },
      { value: "scc_404_88", label: "SCC-404 - 88 t/h" },
      { value: "scc_504_110", label: "SCC-504 - 110 t/h" },
      { value: "scc_505_138", label: "SCC-505 - 138 t/h" },
      { value: "scc_605_165", label: "SCC-605 - 165 t/h" },
      { value: "scc_705_193", label: "SCC-705 - 193 t/h" },
      { value: "scc_707_238", label: "SCC-707 - 238 t/h" },
      { value: "scc_707_plus_264", label: "SCC-707 Plus - 264 t/h" },
    ],
    fornalha: [
      { value: "sem", label: "Sem Fornalha" },
      { value: "com", label: "Com Fornalha Black Velox" },
    ],
    combustiveis: [
      { value: "cavaco", label: "Cavaco" },
      { value: "lenha", label: "Lenha" },
    ],
    alimentador: [
      { value: "sem", label: "Sem Alimentador" },
      { value: "com", label: "Com Alimentador de Cavaco" },
    ],
    volumes: [
      { value: "6_35", label: "6,35 m³" },
      { value: "13", label: "13 m³" },
      { value: "20", label: "20 m³" },
    ],
  };

  const siloPulmaoConfig = {
    silos: [
      { d: 18, a: 5, ton: 120, sacas: 2006 }, { d: 18, a: 6, ton: 140, sacas: 2332 }, { d: 18, a: 7, ton: 160, sacas: 2659 },
      { d: 18, a: 8, ton: 179, sacas: 2986 }, { d: 18, a: 9, ton: 199, sacas: 3312 }, { d: 18, a: 10, ton: 218, sacas: 3639 },
      { d: 21, a: 5, ton: 169, sacas: 2824 }, { d: 21, a: 6, ton: 196, sacas: 3269 }, { d: 21, a: 7, ton: 223, sacas: 3713 },
      { d: 21, a: 8, ton: 249, sacas: 4158 }, { d: 21, a: 9, ton: 276, sacas: 4603 }, { d: 21, a: 10, ton: 303, sacas: 5047 },
      { d: 21, a: 11, ton: 329, sacas: 5492 }, { d: 21, a: 12, ton: 356, sacas: 5936 }, { d: 21, a: 13, ton: 383, sacas: 6381 },
      { d: 21, a: 14, ton: 410, sacas: 6825 }, { d: 24, a: 5, ton: 229, sacas: 3817 }, { d: 24, a: 6, ton: 264, sacas: 4398 },
      { d: 24, a: 7, ton: 299, sacas: 4978 }, { d: 24, a: 8, ton: 334, sacas: 5559 }, { d: 24, a: 9, ton: 368, sacas: 6140 },
      { d: 24, a: 10, ton: 403, sacas: 6720 }, { d: 24, a: 11, ton: 438, sacas: 7301 }, { d: 24, a: 12, ton: 473, sacas: 7882 },
      { d: 24, a: 13, ton: 508, sacas: 8462 }, { d: 24, a: 14, ton: 543, sacas: 9043 }, { d: 30, a: 7, ton: 493, sacas: 8216 },
      { d: 30, a: 8, ton: 548, sacas: 9133 }, { d: 30, a: 9, ton: 603, sacas: 10050 }, { d: 30, a: 10, ton: 658, sacas: 10966 },
      { d: 30, a: 11, ton: 713, sacas: 11883 }, { d: 30, a: 12, ton: 768, sacas: 12800 }, { d: 30, a: 13, ton: 823, sacas: 13717 },
      { d: 30, a: 14, ton: 878, sacas: 14634 }, { d: 30, a: 15, ton: 933, sacas: 15551 }, { d: 30, a: 16, ton: 988, sacas: 16468 },
      { d: 30, a: 17, ton: 1043, sacas: 17385 }, { d: 30, a: 18, ton: 1098, sacas: 18302 }, { d: 36, a: 8, ton: 824, sacas: 13734 },
      { d: 36, a: 9, ton: 903, sacas: 15055 }, { d: 36, a: 10, ton: 983, sacas: 16375 }, { d: 36, a: 11, ton: 1062, sacas: 17695 },
      { d: 36, a: 12, ton: 1141, sacas: 19016 }, { d: 36, a: 13, ton: 1220, sacas: 20336 }, { d: 36, a: 14, ton: 1299, sacas: 21656 },
      { d: 36, a: 15, ton: 1379, sacas: 22977 }, { d: 36, a: 16, ton: 1458, sacas: 24297 },
    ],
    diametros: [18, 21, 24, 30, 36],
    termometrias: [
      { value: "sem", label: "Sem Termometria" },
      { value: "thermo_grain", label: "Thermo Grain" },
      { value: "digital_grain", label: "Digital Grain" },
      { value: "procer", label: "PROCER" },
    ],
    pacotes: [{ value: "pacote_1", label: "Pacote 1" }, { value: "pacote_2", label: "Pacote 2 (estação meteorológica)" }],
    simNao: [{ value: "sim", label: "Sim" }, { value: "nao", label: "Não" }],
    taxas: ["0,08", "0,10", "0,12", "0,16", "0,20", "0,30", "0,40"].map((value) => ({ value, label: value })),
    escadas: [{ value: "marinheiro", label: "Marinheiro" }, { value: "caracol", label: "Caracol" }],
    extras: {
      marinheiro: [{ value: "guarda_corpo_beiral", label: "Guarda corpo de beiral" }],
      caracol: [
        { value: "guarda_corpo_beiral", label: "Guarda corpo de beiral" },
        { value: "monovia_telhado", label: "Monovia do telhado" },
        { value: "pontos_ancoragem", label: "Pontos de ancoragem" },
        { value: "suporte_monope", label: "Suporte para monopé" },
      ],
    },
  };

  function selectedCadastroNome() {
    const option = selects[0].selectedOptions[0];
    return option ? option.dataset.cadastroNome || option.textContent : "";
  }

  function isFluxoSelected() {
    return selectedCadastroNome() === "Item 1 - Fluxo" || selectedPath()[0] === "Fluxo";
  }

  function isTransportadorSelected() {
    return selectedCadastroNome() === "Item 2 - Transportadores" || selectedPath()[0] === "Transportadores";
  }

  function isMaquinaLimpezaSelected() {
    return (
      selectedCadastroNome() === "Item 3 - Máquina de Limpeza Grain Cleaner EC" ||
      selectedPath()[0] === "Máquina de Limpeza Grain Cleaner EC"
    );
  }

  function isSecadorSelected() {
    return selectedCadastroNome() === "Item 4 - Secadores Process Dryer" || selectedPath()[0] === "Secadores Process Dryer";
  }

  function isSiloPulmaoSelected() {
    return selectedCadastroNome() === "Item 5 - Silo Pulmão Elevado" || selectedPath()[0] === "Silo Pulmão Elevado";
  }

  function setVariationFieldsVisible(visible) {
    variationLabels.forEach((label) => {
      label.hidden = !visible;
    });
    if (!visible) {
      for (let index = 1; index < selects.length; index += 1) {
        resetSelect(selects[index], selects[index].dataset.placeholder || "Selecione");
      }
    }
  }

  function setFinalFieldsVisible(visible) {
    finalFields.forEach((element) => {
      element.hidden = !visible;
      element.querySelectorAll("input, select, textarea, button").forEach((field) => {
        field.disabled = !visible;
      });
    });
  }

  function resetSelect(select, placeholder) {
    select.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    select.appendChild(option);
    select.disabled = true;
  }

  function setOptions(select, items, selectedId) {
    const placeholder = select.dataset.placeholder || "Selecione";
    resetSelect(select, placeholder);
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.nome;
      option.selected = String(selectedId || "") === String(item.id);
      select.appendChild(option);
    });
    select.disabled = items.length === 0;
  }

  async function fetchJson(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Falha ao carregar dados");
    return response.json();
  }

  function selectedPath() {
    return selects
      .filter((select) => select.value)
      .map((select) => select.options[select.selectedIndex].textContent);
  }

  function updatePath() {
    const path = selectedPath();
    pathBox.textContent = path.length ? path.join(" > ") : "";
  }

  function renderAttributes(attrs) {
    attrsBox.innerHTML = "";
    if (!attrs.length) {
      attrsBox.innerHTML = '<p class="muted">Nenhum atributo tecnico cadastrado para este item.</p>';
      return;
    }

    const title = document.createElement("h3");
    title.textContent = "Dados carregados";
    attrsBox.appendChild(title);

    const list = document.createElement("dl");
    list.className = "loaded-attributes-grid";
    attrs.forEach((attr) => {
      const item = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = attr.nome;
      const value = attr.valor || "-";
      dd.textContent = attr.unidade ? `${value} ${attr.unidade}` : value;
      item.appendChild(dt);
      item.appendChild(dd);
      list.appendChild(item);
    });
    attrsBox.appendChild(list);
  }

  async function loadAttributes(equipmentId) {
    if (!equipmentId) {
      attrsBox.innerHTML = "";
      return;
    }
    const attrs = await fetchJson(`/equipamentos/${equipmentId}/atributos`);
    renderAttributes(attrs);
  }

  function fluxoOptionByKey(options) {
    return options.reduce((map, option) => {
      map[option.chave] = option;
      return map;
    }, {});
  }

  function savedOptionValue(option) {
    const saved = selectedOptions[String(option.id)] || {};
    return saved.valor || "";
  }

  function fluxoHidden(option, value, disabled) {
    const fragment = document.createDocumentFragment();
    const present = document.createElement("input");
    present.type = "hidden";
    present.name = `opcao_presente__${option.id}`;
    present.value = "1";
    present.disabled = Boolean(disabled);

    const input = document.createElement("input");
    input.type = "hidden";
    input.name = `opcao__${option.id}`;
    input.value = value || "";
    input.disabled = Boolean(disabled);

    fragment.appendChild(present);
    fragment.appendChild(input);
    return { fragment, input, present };
  }

  function makeFluxoCard(label, value, selected, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "choice-card";
    button.dataset.value = value;
    button.setAttribute("aria-pressed", selected ? "true" : "false");
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
  }

  function makeFluxoStep(titleText, option, choices, currentValue, onChange) {
    const step = document.createElement("section");
    step.className = "fluxo-step";

    const title = document.createElement("h4");
    title.textContent = titleText;
    step.appendChild(title);

    const hidden = fluxoHidden(option, currentValue);
    step.appendChild(hidden.fragment);

    const grid = document.createElement("div");
    grid.className = "choice-card-grid";
    choices.forEach((choice) => {
      grid.appendChild(
        makeFluxoCard(choice.label, choice.value, currentValue === choice.value, () => {
          hidden.input.value = choice.value;
          onChange(choice.value);
        })
      );
    });
    step.appendChild(grid);
    return step;
  }

  function setSelectedEquipment(option) {
    selects[0].value = option.value;
    chooseLevel(0).catch(() => {
      attrsBox.innerHTML = '<p class="muted">Nao foi possivel carregar os dados do equipamento.</p>';
    });
  }

  function renderEquipmentPicker() {
    optionsBox.innerHTML = "";
    setFinalFieldsVisible(false);
    const wrap = document.createElement("div");
    wrap.className = "fluxo-wizard";
    const title = document.createElement("h3");
    title.textContent = "Adicionar item";
    wrap.appendChild(title);

    const step = document.createElement("section");
    step.className = "fluxo-step";
    const heading = document.createElement("h4");
    heading.textContent = "Escolha o item";
    step.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "choice-card-grid";
    Array.from(selects[0].options)
      .filter((option) => option.value)
      .forEach((option) => {
        grid.appendChild(
          makeFluxoCard(option.textContent, option.value, false, () => {
            setSelectedEquipment(option);
          })
        );
      });
    step.appendChild(grid);
    wrap.appendChild(step);
    optionsBox.appendChild(wrap);
  }

  function renderFluxoOptions(options) {
    const optionMap = fluxoOptionByKey(options);
    const tipo = optionMap.tipo_fluxo;
    const graos = optionMap.fluxo_graos;
    const impurezasToggle = optionMap.fluxo_impurezas_habilitado;
    const impurezas = optionMap.fluxo_impurezas;
    const moega = optionMap.moega;
    const requiredOptions = [tipo, graos, impurezasToggle, impurezas, moega];
    if (requiredOptions.some((option) => !option)) {
      optionsBox.innerHTML = '<p class="muted">Configuracao do Fluxo incompleta.</p>';
      setFinalFieldsVisible(false);
      return;
    }

    const state = {
      tipo: savedOptionValue(tipo),
      graos: savedOptionValue(graos),
      impurezasToggle: savedOptionValue(impurezasToggle) || "",
      impurezas: savedOptionValue(impurezas),
      moega: savedOptionValue(moega),
    };

    function isComplete() {
      return Boolean(
        state.tipo &&
          state.graos &&
          state.impurezasToggle &&
          (state.impurezasToggle === "nao" || state.impurezas) &&
          state.moega
      );
    }

    function rerender() {
      optionsBox.innerHTML = "";
      setFinalFieldsVisible(isComplete());

      const wrap = document.createElement("div");
      wrap.className = "fluxo-wizard";
      const title = document.createElement("h3");
      title.textContent = "Adicionar Fluxo";
      wrap.appendChild(title);

      wrap.appendChild(
        makeFluxoStep("Etapa 1 - Tipo de Fluxo", tipo, tipo.valores.map((value) => ({
          label: value.rotulo,
          value: value.valor,
        })), state.tipo, (value) => {
          state.tipo = value;
          state.graos = "";
          state.impurezasToggle = "";
          state.impurezas = "";
          state.moega = "";
          rerender();
        })
      );

      if (state.tipo) {
        wrap.appendChild(
          makeFluxoStep("Etapa 2 - Fluxo de Grãos", graos, graos.valores.map((value) => ({
            label: value.rotulo,
            value: value.valor,
          })), state.graos, (value) => {
            state.graos = value;
            state.impurezasToggle = "";
            state.impurezas = "";
            state.moega = "";
            rerender();
          })
        );
      }

      if (state.graos) {
        wrap.appendChild(
          makeFluxoStep("Etapa 3 - Fluxo de Impurezas", impurezasToggle, [
            { label: "Sem fluxo de impurezas", value: "nao" },
            { label: "Com fluxo de impurezas", value: "sim" },
          ], state.impurezasToggle, (value) => {
            state.impurezasToggle = value;
            state.impurezas = "";
            state.moega = "";
            rerender();
          })
        );
      }

      if (state.impurezasToggle === "sim") {
        wrap.appendChild(
          makeFluxoStep("Etapa 3.1 - Capacidade do Fluxo de Impurezas", impurezas, impurezas.valores.map((value) => ({
            label: value.rotulo,
            value: value.valor,
          })), state.impurezas, (value) => {
            state.impurezas = value;
            state.moega = "";
            rerender();
          })
        );
      } else {
        const hidden = fluxoHidden(impurezas, "", true);
        wrap.appendChild(hidden.fragment);
      }

      if (state.impurezasToggle === "nao" || state.impurezas) {
        wrap.appendChild(
          makeFluxoStep("Etapa 4 - Moega", moega, moega.valores.map((value) => ({
            label: value.rotulo,
            value: value.valor,
          })), state.moega, (value) => {
            state.moega = value;
            rerender();
          })
        );
      }

      optionsBox.appendChild(wrap);
    }

    rerender();
  }

  function transportadorTipo(value) {
    return transportadorConfig.tipos.find((tipo) => tipo.value === value);
  }

  function transportadorCamposIniciais() {
    const sensores = selectedCampos.sensores_acessorios || [];
    return {
      tipo: selectedCampos.tipo || "",
      subtipo: selectedCampos.subtipo || "",
      itens: sensores.map((item) => item.chave).filter(Boolean),
      obs: sensores.reduce((map, item) => {
        if (item.chave) map[item.chave] = item.observacao || "";
        return map;
      }, {}),
    };
  }

  function hiddenInput(name, value) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value || "";
    return input;
  }

  function renderTransportadorOptions() {
    const state = transportadorCamposIniciais();

    function tipoCompleto() {
      const tipo = transportadorTipo(state.tipo);
      if (!tipo) return false;
      return !tipo.subtipos.length || Boolean(state.subtipo);
    }

    function isComplete() {
      return Boolean(state.tipo && tipoCompleto());
    }

    function cleanIncompatibleItems() {
      const permitidos = new Set(transportadorConfig.itens[state.tipo] || []);
      state.itens = state.itens.filter((item) => permitidos.has(item));
      Object.keys(state.obs).forEach((key) => {
        if (!permitidos.has(key)) delete state.obs[key];
      });
    }

    function renderHiddenFields(container) {
      container.appendChild(hiddenInput("transportador_tipo", state.tipo));
      container.appendChild(hiddenInput("transportador_subtipo", state.subtipo));
      state.itens.forEach((item) => {
        container.appendChild(hiddenInput("transportador_item", item));
        container.appendChild(hiddenInput(`transportador_obs__${item}`, state.obs[item] || ""));
      });
    }

    function renderStep(titleText, choices, currentValue, onChange) {
      const step = document.createElement("section");
      step.className = "fluxo-step";
      const title = document.createElement("h4");
      title.textContent = titleText;
      step.appendChild(title);
      const grid = document.createElement("div");
      grid.className = "choice-card-grid";
      choices.forEach((choice) => {
        grid.appendChild(makeFluxoCard(choice.label, choice.value, currentValue === choice.value, () => onChange(choice.value)));
      });
      step.appendChild(grid);
      return step;
    }

    function renderChecklist() {
      const step = document.createElement("section");
      step.className = "fluxo-step";
      const title = document.createElement("h4");
      title.textContent = "Sensores e acessórios compatíveis";
      step.appendChild(title);
      const itens = transportadorConfig.itens[state.tipo] || [];
      if (!itens.length) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = "Nenhum sensor/acessório por enquanto.";
        step.appendChild(empty);
        return step;
      }
      const list = document.createElement("div");
      list.className = "transport-checklist";
      itens.forEach((key) => {
        const detail = transportadorConfig.detalhes[key];
        const row = document.createElement("div");
        row.className = "transport-check-card";
        row.dataset.checked = state.itens.includes(key) ? "true" : "false";
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = detail.label;
        button.addEventListener("click", () => {
          if (state.itens.includes(key)) {
            state.itens = state.itens.filter((item) => item !== key);
            delete state.obs[key];
          } else {
            state.itens.push(key);
          }
          rerender();
        });
        const obs = document.createElement("input");
        obs.placeholder = "Observação";
        obs.value = state.obs[key] || "";
        obs.disabled = !state.itens.includes(key);
        obs.addEventListener("input", () => {
          state.obs[key] = obs.value;
          const hiddenObs = optionsBox.querySelector(`[name="transportador_obs__${key}"]`);
          if (hiddenObs) hiddenObs.value = obs.value;
        });
        row.appendChild(button);
        row.appendChild(obs);
        list.appendChild(row);
      });
      step.appendChild(list);
      return step;
    }

    function rerender() {
      cleanIncompatibleItems();
      optionsBox.innerHTML = "";
      setFinalFieldsVisible(isComplete());
      const wrap = document.createElement("div");
      wrap.className = "fluxo-wizard";
      const title = document.createElement("h3");
      title.textContent = "Adicionar Transportador";
      wrap.appendChild(title);
      renderHiddenFields(wrap);

      wrap.appendChild(
        renderStep("Etapa 1 - Tipo de Transportador", transportadorConfig.tipos, state.tipo, (value) => {
          state.tipo = value;
          state.subtipo = "";
          state.itens = [];
          state.obs = {};
          rerender();
        })
      );

      const tipo = transportadorTipo(state.tipo);
      if (tipo && tipo.subtipos.length) {
        wrap.appendChild(
          renderStep("Etapa 2 - Subtipo", tipo.subtipos, state.subtipo, (value) => {
            state.subtipo = value;
            state.itens = [];
            state.obs = {};
            rerender();
          })
        );
      }

      if (state.tipo && tipoCompleto()) {
        wrap.appendChild(renderChecklist());
      }

      optionsBox.appendChild(wrap);
    }

    rerender();
  }

  function renderMaquinaLimpezaOptions() {
    const state = {
      tipo: selectedCampos.tipo_limpeza || "",
      modelo: selectedCampos.modelo || "",
    };

    function isComplete() {
      return Boolean(state.tipo && state.modelo);
    }

    function renderHiddenFields(container) {
      container.appendChild(hiddenInput("maquina_limpeza_tipo", state.tipo));
      container.appendChild(hiddenInput("maquina_limpeza_modelo", state.modelo));
    }

    function renderStep(titleText, choices, currentValue, onChange) {
      const step = document.createElement("section");
      step.className = "fluxo-step";
      const title = document.createElement("h4");
      title.textContent = titleText;
      step.appendChild(title);
      const grid = document.createElement("div");
      grid.className = "choice-card-grid";
      choices.forEach((choice) => {
        grid.appendChild(makeFluxoCard(choice.label, choice.value, currentValue === choice.value, () => onChange(choice.value)));
      });
      step.appendChild(grid);
      return step;
    }

    function rerender() {
      optionsBox.innerHTML = "";
      setFinalFieldsVisible(isComplete());
      const wrap = document.createElement("div");
      wrap.className = "fluxo-wizard";
      const title = document.createElement("h3");
      title.textContent = "Máquina de Limpeza Grain Cleaner EC";
      wrap.appendChild(title);
      renderHiddenFields(wrap);

      wrap.appendChild(
        renderStep("Etapa 1 - Tipo de Limpeza", maquinaLimpezaConfig.tipos, state.tipo, (value) => {
          state.tipo = value;
          state.modelo = "";
          rerender();
        })
      );

      if (state.tipo) {
        wrap.appendChild(
          renderStep("Etapa 2 - Modelo", maquinaLimpezaConfig.modelos[state.tipo] || [], state.modelo, (value) => {
            state.modelo = value;
            rerender();
          })
        );
      }

      optionsBox.appendChild(wrap);
    }

    rerender();
  }

  function renderSecadorOptions() {
    const state = {
      modelo: selectedCampos.modelo || "",
      fornalha: selectedCampos.fornalha || "",
      combustivel: selectedCampos.combustivel || "",
      alimentador: selectedCampos.alimentador || "",
      volume: selectedCampos.alimentador_volume || "",
    };

    function isComplete() {
      return Boolean(
        state.modelo &&
          state.fornalha &&
          (state.fornalha === "sem" || state.combustivel) &&
          state.alimentador &&
          (state.alimentador === "sem" || state.volume)
      );
    }

    function renderHiddenFields(container) {
      container.appendChild(hiddenInput("secador_modelo", state.modelo));
      container.appendChild(hiddenInput("secador_fornalha", state.fornalha));
      container.appendChild(hiddenInput("secador_combustivel", state.combustivel));
      container.appendChild(hiddenInput("secador_alimentador", state.alimentador));
      container.appendChild(hiddenInput("secador_alimentador_volume", state.volume));
    }

    function renderStep(titleText, choices, currentValue, onChange) {
      const step = document.createElement("section");
      step.className = "fluxo-step";
      const title = document.createElement("h4");
      title.textContent = titleText;
      step.appendChild(title);
      const grid = document.createElement("div");
      grid.className = "choice-card-grid";
      choices.forEach((choice) => {
        grid.appendChild(makeFluxoCard(choice.label, choice.value, currentValue === choice.value, () => onChange(choice.value)));
      });
      step.appendChild(grid);
      return step;
    }

    function rerender() {
      optionsBox.innerHTML = "";
      setFinalFieldsVisible(isComplete());
      const wrap = document.createElement("div");
      wrap.className = "fluxo-wizard";
      const title = document.createElement("h3");
      title.textContent = "Secadores Process Dryer";
      wrap.appendChild(title);
      renderHiddenFields(wrap);

      wrap.appendChild(
        renderStep("Etapa 1 - Modelo do Secador", secadorConfig.modelos, state.modelo, (value) => {
          state.modelo = value;
          state.fornalha = "";
          state.combustivel = "";
          state.alimentador = "";
          state.volume = "";
          rerender();
        })
      );

      if (state.modelo) {
        wrap.appendChild(
          renderStep("Etapa 2 - Fornalha Black Velox", secadorConfig.fornalha, state.fornalha, (value) => {
            state.fornalha = value;
            state.combustivel = "";
            state.alimentador = "";
            state.volume = "";
            rerender();
          })
        );
      }

      if (state.fornalha === "com") {
        wrap.appendChild(
          renderStep("Tipo de combustível", secadorConfig.combustiveis, state.combustivel, (value) => {
            state.combustivel = value;
            state.alimentador = "";
            state.volume = "";
            rerender();
          })
        );
      }

      if (state.fornalha === "sem" || state.combustivel) {
        wrap.appendChild(
          renderStep("Etapa 3 - Alimentador de Cavaco", secadorConfig.alimentador, state.alimentador, (value) => {
            state.alimentador = value;
            state.volume = "";
            rerender();
          })
        );
      }

      if (state.alimentador === "com") {
        wrap.appendChild(
          renderStep("Volume do Alimentador de Cavaco", secadorConfig.volumes, state.volume, (value) => {
            state.volume = value;
            rerender();
          })
        );
      }

      optionsBox.appendChild(wrap);
    }

    rerender();
  }

  function renderSiloPulmaoOptions() {
    const state = {
      modo: selectedCampos.modo || "",
      diametro: selectedCampos.diametro || "",
      capacidadeTipo: selectedCampos.capacidade_tipo || "",
      capacidadeDesejada: selectedCampos.capacidade_desejada || "",
      silo: selectedCampos.diametro ? { d: Number(selectedCampos.diametro), a: Number(selectedCampos.aneis), ton: Number(selectedCampos.ton), sacas: Number(String(selectedCampos.sacas || "").replace(/\D/g, "")) } : null,
      termometria: selectedCampos.termometria || "",
      pacote: selectedCampos.termometria_pacote || "",
      sensorNivel: selectedCampos.sensor_nivel || "",
      aeracao: selectedCampos.aeracao || "",
      taxa: selectedCampos.aeracao_taxa || "",
      escada: selectedCampos.escada || "",
      alternarEscadas: selectedCampos.alternar_escadas || "",
      extras: (selectedCampos.escada_extras || []).map((item) => item.chave).filter(Boolean),
    };

    if (quantidadeInput) {
      quantidadeInput.oninput = () => {
        if (isSiloPulmaoSelected()) {
          rerender();
        }
      };
    }

    const fmt = (value) => Number(value || 0).toLocaleString("pt-BR");
    const resetAccessories = () => {
      state.termometria = ""; state.pacote = ""; state.sensorNivel = ""; state.aeracao = ""; state.taxa = ""; state.escada = ""; state.extras = [];
    };
    const complete = () => Boolean(state.silo && state.termometria && (state.termometria === "sem" || state.pacote) && state.sensorNivel && state.aeracao && (state.aeracao === "nao" || state.taxa) && state.escada);

    function renderHiddenFields(container) {
      container.appendChild(hiddenInput("silo_modo", state.modo));
      container.appendChild(hiddenInput("silo_diametro", state.silo ? String(state.silo.d) : ""));
      container.appendChild(hiddenInput("silo_aneis", state.silo ? String(state.silo.a) : ""));
      container.appendChild(hiddenInput("silo_ton", state.silo ? String(state.silo.ton) : ""));
      container.appendChild(hiddenInput("silo_sacas", state.silo ? fmt(state.silo.sacas) : ""));
      container.appendChild(hiddenInput("silo_capacidade_tipo", state.capacidadeTipo));
      container.appendChild(hiddenInput("silo_capacidade_desejada", state.capacidadeDesejada));
      container.appendChild(hiddenInput("silo_termometria", state.termometria));
      container.appendChild(hiddenInput("silo_termometria_pacote", state.pacote));
      container.appendChild(hiddenInput("silo_sensor_nivel", state.sensorNivel));
      container.appendChild(hiddenInput("silo_aeracao", state.aeracao));
      container.appendChild(hiddenInput("silo_aeracao_taxa", state.taxa));
      container.appendChild(hiddenInput("silo_escada", state.escada));
      container.appendChild(hiddenInput("silo_alternar_escadas", state.alternarEscadas));
      state.extras.forEach((extra) => container.appendChild(hiddenInput("silo_escada_extra", extra)));
    }

    function renderStep(titleText, choices, currentValue, onChange) {
      const step = document.createElement("section");
      step.className = "fluxo-step";
      const title = document.createElement("h4");
      title.textContent = titleText;
      step.appendChild(title);
      const grid = document.createElement("div");
      grid.className = "choice-card-grid";
      choices.forEach((choice) => grid.appendChild(makeFluxoCard(choice.label, choice.value, currentValue === choice.value, () => onChange(choice.value))));
      step.appendChild(grid);
      return step;
    }

    function siloChoiceCard(silo) {
      const selected = state.silo && state.silo.d === silo.d && state.silo.a === silo.a;
      const button = makeFluxoCard("", `${silo.d}_${silo.a}`, selected, () => {
        state.silo = silo;
        state.diametro = String(silo.d);
        resetAccessories();
        rerender();
      });
      button.classList.add("silo-card");
      button.innerHTML = `<strong>${silo.d} ft | ${silo.a} anéis</strong><span>${fmt(silo.ton)} Ton</span><span>${fmt(silo.sacas)} scs</span>`;
      return button;
    }

    function renderSiloChoices(container) {
      if (state.modo === "diametro" && state.diametro) {
        const step = document.createElement("section");
        step.className = "fluxo-step";
        const title = document.createElement("h4");
        title.textContent = "Etapa 3 - Anéis";
        step.appendChild(title);
        const grid = document.createElement("div");
        grid.className = "choice-card-grid";
        siloPulmaoConfig.silos.filter((silo) => String(silo.d) === state.diametro).forEach((silo) => grid.appendChild(siloChoiceCard(silo)));
        step.appendChild(grid);
        container.appendChild(step);
      }
      if (state.modo === "capacidade" && state.capacidadeTipo) {
        const step = document.createElement("section");
        step.className = "fluxo-step";
        const title = document.createElement("h4");
        title.textContent = "Etapa 3 - Capacidade desejada";
        step.appendChild(title);
        const input = document.createElement("input");
        input.type = "number";
        input.min = "0";
        input.placeholder = state.capacidadeTipo === "sacas" ? "Ex.: 20000" : "Ex.: 1200";
        input.value = state.capacidadeDesejada;
        step.appendChild(input);
        const suggestionsBox = document.createElement("div");
        suggestionsBox.className = "choice-card-grid";
        step.appendChild(suggestionsBox);

        function updateSuggestions() {
          suggestionsBox.innerHTML = "";
          const alvo = Number(String(state.capacidadeDesejada || "").replace(",", "."));
          if (!alvo) return;
          const key = state.capacidadeTipo === "sacas" ? "sacas" : "ton";
          const menores = siloPulmaoConfig.silos.filter((silo) => silo[key] <= alvo).sort((a, b) => b[key] - a[key]).slice(0, 4).reverse();
          const maiores = siloPulmaoConfig.silos.filter((silo) => silo[key] > alvo).sort((a, b) => a[key] - b[key]).slice(0, 4);
          [...menores, ...maiores].forEach((silo) => suggestionsBox.appendChild(siloChoiceCard(silo)));
        }
        input.addEventListener("input", () => {
          state.capacidadeDesejada = input.value;
          state.silo = null;
          resetAccessories();
          updateSuggestions();
        });
        updateSuggestions();
        container.appendChild(step);
      }
    }

    function renderExtraCards(container) {
      const extras = siloPulmaoConfig.extras[state.escada] || [];
      if (!extras.length) return;
      const step = document.createElement("section");
      step.className = "fluxo-step";
      const title = document.createElement("h4");
      title.textContent = "Itens da escada";
      step.appendChild(title);
      const grid = document.createElement("div");
      grid.className = "choice-card-grid";
      extras.forEach((extra) => grid.appendChild(makeFluxoCard(extra.label, extra.value, state.extras.includes(extra.value), () => {
        state.extras = state.extras.includes(extra.value) ? state.extras.filter((item) => item !== extra.value) : [...state.extras, extra.value];
        rerender();
      })));
      step.appendChild(grid);
      container.appendChild(step);
    }

    function rerender() {
      optionsBox.innerHTML = "";
      setFinalFieldsVisible(complete());
      const wrap = document.createElement("div");
      wrap.className = "fluxo-wizard";
      const title = document.createElement("h3");
      title.textContent = "Silo Pulmão Elevado";
      wrap.appendChild(title);
      renderHiddenFields(wrap);

      wrap.appendChild(renderStep("Etapa 1 - Modo de Seleção", [{ value: "diametro", label: "Selecionar por Diâmetro" }, { value: "capacidade", label: "Selecionar por Capacidade" }], state.modo, (value) => {
        state.modo = value; state.diametro = ""; state.capacidadeTipo = ""; state.capacidadeDesejada = ""; state.silo = null; resetAccessories(); rerender();
      }));
      if (state.modo === "diametro") {
        wrap.appendChild(renderStep("Etapa 2 - Diâmetro (ft)", siloPulmaoConfig.diametros.map((d) => ({ value: String(d), label: String(d) })), state.diametro, (value) => {
          state.diametro = value; state.silo = null; resetAccessories(); rerender();
        }));
      }
      if (state.modo === "capacidade") {
        wrap.appendChild(renderStep("Etapa 2 - Tipo de capacidade", [{ value: "ton", label: "Toneladas" }, { value: "sacas", label: "Sacas 60kg" }], state.capacidadeTipo, (value) => {
          state.capacidadeTipo = value; state.capacidadeDesejada = ""; state.silo = null; resetAccessories(); rerender();
        }));
      }
      renderSiloChoices(wrap);
      if (state.silo) wrap.appendChild(renderStep("Termometria", siloPulmaoConfig.termometrias, state.termometria, (value) => { state.termometria = value; state.pacote = ""; state.sensorNivel = ""; state.aeracao = ""; state.taxa = ""; state.escada = ""; state.extras = []; rerender(); }));
      if (state.termometria && state.termometria !== "sem") wrap.appendChild(renderStep("Pacote", siloPulmaoConfig.pacotes, state.pacote, (value) => { state.pacote = value; rerender(); }));
      if (state.termometria === "sem" || state.pacote) wrap.appendChild(renderStep("Sensor de Nível", siloPulmaoConfig.simNao, state.sensorNivel, (value) => { state.sensorNivel = value; state.aeracao = ""; state.taxa = ""; state.escada = ""; state.extras = []; rerender(); }));
      if (state.sensorNivel) wrap.appendChild(renderStep("Aeração", siloPulmaoConfig.simNao, state.aeracao, (value) => { state.aeracao = value; state.taxa = ""; state.escada = ""; state.extras = []; rerender(); }));
      if (state.aeracao === "sim") wrap.appendChild(renderStep("Taxa de Aeração", siloPulmaoConfig.taxas, state.taxa, (value) => { state.taxa = value; rerender(); }));
      if (state.aeracao === "nao" || state.taxa) wrap.appendChild(renderStep("Tipo de Escada", siloPulmaoConfig.escadas, state.escada, (value) => { state.escada = value; state.alternarEscadas = ""; state.extras = []; rerender(); }));
      if (Number(quantidadeInput ? quantidadeInput.value : 1) <= 1) {
        state.alternarEscadas = "";
      }
      if (state.escada && Number(quantidadeInput ? quantidadeInput.value : 1) > 1) {
        wrap.appendChild(renderStep("Alternar escadas caracol e marinheiro?", siloPulmaoConfig.simNao, state.alternarEscadas, (value) => { state.alternarEscadas = value; rerender(); }));
      }
      if (state.escada) renderExtraCards(wrap);
      optionsBox.appendChild(wrap);
    }

    rerender();
  }

  function renderOptions(options) {
    optionsBox.innerHTML = "";
    if (isFluxoSelected()) {
      renderFluxoOptions(options);
      return;
    }
    if (isTransportadorSelected()) {
      renderTransportadorOptions();
      return;
    }
    if (isMaquinaLimpezaSelected()) {
      renderMaquinaLimpezaOptions();
      return;
    }
    if (isSecadorSelected()) {
      renderSecadorOptions();
      return;
    }
    if (isSiloPulmaoSelected()) {
      renderSiloPulmaoOptions();
      return;
    }
    if (!options.length) {
      optionsBox.innerHTML = '<p class="muted">Nenhuma configuracao cadastrada para este item.</p>';
      return;
    }

    const title = document.createElement("h3");
    title.textContent = "Configuracoes do item";
    optionsBox.appendChild(title);

    const grid = document.createElement("div");
    grid.className = "options-grid";

    options.forEach((option) => {
      const saved = selectedOptions[String(option.id)] || {};
      const label = document.createElement("label");
      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = `opcao_presente__${option.id}`;
      hidden.value = "1";
      label.dataset.optionId = String(option.id);
      if (option.dependencia) {
        label.dataset.dependsOptionId = String(option.dependencia.depende_opcao_id);
        label.dataset.dependsValue = option.dependencia.depende_valor;
      }
      label.textContent = option.nome;
      label.appendChild(hidden);

      if (option.tipo === "booleano" && option.chave === "fluxo_impurezas_habilitado") {
        const select = document.createElement("select");
        select.name = `opcao__${option.id}`;
        const no = document.createElement("option");
        no.value = "nao";
        no.textContent = "Não";
        no.selected = saved.valor !== "sim";
        const yes = document.createElement("option");
        yes.value = "sim";
        yes.textContent = "Sim";
        yes.selected = saved.valor === "sim";
        select.appendChild(no);
        select.appendChild(yes);
        label.appendChild(select);
      } else if (option.tipo === "booleano") {
        label.className = "option-check";
        label.textContent = "";
        label.appendChild(hidden);
        const input = document.createElement("input");
        input.type = "checkbox";
        input.name = `opcao__${option.id}`;
        input.value = "sim";
        input.checked = saved.valor === "sim";
        label.appendChild(input);
        label.appendChild(document.createTextNode(option.nome));
      } else if (option.tipo === "selecao") {
        const select = document.createElement("select");
        select.name = `opcao__${option.id}`;
        select.required = Boolean(option.obrigatorio);
        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = "Selecione";
        select.appendChild(empty);
        (option.valores || []).forEach((value) => {
          const item = document.createElement("option");
          item.value = value.valor;
          item.textContent = value.rotulo;
          item.selected = saved.valor === value.valor;
          select.appendChild(item);
        });
        label.appendChild(select);
      } else {
        const input = document.createElement("input");
        input.name = `opcao__${option.id}`;
        input.type = option.tipo === "numero" ? "number" : "text";
        input.value = saved.valor || "";
        input.required = Boolean(option.obrigatorio);
        label.appendChild(input);
      }

      grid.appendChild(label);
    });

    optionsBox.appendChild(grid);
    bindOptionDependencies();
  }

  function optionValue(optionId) {
    const field = optionsBox.querySelector(`[name="opcao__${optionId}"]`);
    if (!field) return "";
    if (field.type === "checkbox") return field.checked ? "sim" : "nao";
    return field.value || "";
  }

  function setOptionEnabled(label, enabled) {
    label.hidden = !enabled;
    label.querySelectorAll("input, select, textarea").forEach((field) => {
      field.disabled = !enabled;
      if (!enabled && field.type === "checkbox") field.checked = false;
      if (!enabled && field.tagName !== "INPUT") field.value = "";
      if (!enabled && field.type !== "hidden" && field.type !== "checkbox") field.value = "";
    });
  }

  function applyOptionDependencies() {
    optionsBox.querySelectorAll("[data-option-id]").forEach((label) => {
      const dependsOptionId = label.dataset.dependsOptionId;
      const dependsValue = label.dataset.dependsValue;
      if (!dependsOptionId || !dependsValue) {
        setOptionEnabled(label, true);
        return;
      }
      setOptionEnabled(label, optionValue(dependsOptionId) === dependsValue);
    });
  }

  function bindOptionDependencies() {
    optionsBox.querySelectorAll("input, select, textarea").forEach((field) => {
      field.addEventListener("change", applyOptionDependencies);
      field.addEventListener("input", applyOptionDependencies);
    });
    applyOptionDependencies();
  }

  async function loadOptions(equipmentId) {
    if (!equipmentId) {
      optionsBox.innerHTML = "";
      return;
    }
    const options = await fetchJson(`/equipamentos/${equipmentId}/opcoes`);
    renderOptions(options);
  }

  async function loadChildren(level, parentId, selectedId) {
    const next = selects[level + 1];
    if (!next) return [];
    resetSelect(next, next.dataset.placeholder || "Selecione");
    for (let index = level + 2; index < selects.length; index += 1) {
      resetSelect(selects[index], selects[index].dataset.placeholder || "Selecione");
    }
    if (!parentId) return [];

    const children = await fetchJson(`/equipamentos/${parentId}/filhos`);
    setOptions(next, children, selectedId);
    return children;
  }

  async function chooseLevel(level) {
    const selectedId = selects[level].value;
    finalInput.value = "";
    attrsBox.innerHTML = "";
    optionsBox.innerHTML = "";

    if (!selectedId) {
      setVariationFieldsVisible(true);
      setFinalFieldsVisible(true);
      for (let index = level + 1; index < selects.length; index += 1) {
        resetSelect(selects[index], selects[index].dataset.placeholder || "Selecione");
      }
      updatePath();
      return;
    }

    if (level === 0 && isFluxoSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedId;
      pathBox.textContent = "Fluxo";
      attrsBox.innerHTML = "";
      await loadOptions(selectedId);
      return;
    }

    if (level === 0 && isTransportadorSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedId;
      pathBox.textContent = "Transportadores";
      attrsBox.innerHTML = "";
      await loadOptions(selectedId);
      return;
    }

    if (level === 0 && isMaquinaLimpezaSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedId;
      pathBox.textContent = "Máquina de Limpeza Grain Cleaner EC";
      attrsBox.innerHTML = "";
      await loadOptions(selectedId);
      return;
    }

    if (level === 0 && isSecadorSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedId;
      pathBox.textContent = "Secadores Process Dryer";
      attrsBox.innerHTML = "";
      await loadOptions(selectedId);
      return;
    }

    if (level === 0 && isSiloPulmaoSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedId;
      pathBox.textContent = "Silo Pulmão Elevado";
      attrsBox.innerHTML = "";
      await loadOptions(selectedId);
      return;
    }

    setVariationFieldsVisible(true);
    setFinalFieldsVisible(true);
    const children = await loadChildren(level, selectedId);
    if (!children.length || level === selects.length - 1) {
      finalInput.value = selectedId;
      await loadAttributes(selectedId);
      await loadOptions(selectedId);
    }
    updatePath();
  }

  selects.forEach((select, level) => {
    select.addEventListener("change", () => {
      chooseLevel(level).catch(() => {
        attrsBox.innerHTML = '<p class="muted">Nao foi possivel carregar os dados do equipamento.</p>';
      });
    });
  });

  form.addEventListener("submit", (event) => {
    if (!finalInput.value) {
      event.preventDefault();
      attrsBox.innerHTML = '<p class="muted">Selecione o modelo final antes de adicionar ao anteprojeto.</p>';
      return;
    }
    if (
      (isFluxoSelected() || isTransportadorSelected() || isMaquinaLimpezaSelected() || isSecadorSelected() || isSiloPulmaoSelected()) &&
      finalFields.some((element) => element.hidden)
    ) {
      event.preventDefault();
      attrsBox.innerHTML = "";
      const alert = document.createElement("p");
      alert.className = "muted";
      alert.textContent = "Complete todas as etapas antes de adicionar ao anteprojeto.";
      optionsBox.appendChild(alert);
    }
  });

  async function preloadSelection() {
    if (!selectedChain.length) return;
    selects[0].value = selectedChain[0].id;
    if (isFluxoSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedChain[0].id;
      pathBox.textContent = "Fluxo";
      attrsBox.innerHTML = "";
      await loadOptions(finalInput.value);
      return;
    }
    if (isTransportadorSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedChain[0].id;
      pathBox.textContent = "Transportadores";
      attrsBox.innerHTML = "";
      await loadOptions(finalInput.value);
      return;
    }
    if (isMaquinaLimpezaSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedChain[0].id;
      pathBox.textContent = "Máquina de Limpeza Grain Cleaner EC";
      attrsBox.innerHTML = "";
      await loadOptions(finalInput.value);
      return;
    }
    if (isSecadorSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedChain[0].id;
      pathBox.textContent = "Secadores Process Dryer";
      attrsBox.innerHTML = "";
      await loadOptions(finalInput.value);
      return;
    }
    if (isSiloPulmaoSelected()) {
      setVariationFieldsVisible(false);
      setFinalFieldsVisible(false);
      finalInput.value = selectedChain[0].id;
      pathBox.textContent = "Silo Pulmão Elevado";
      attrsBox.innerHTML = "";
      await loadOptions(finalInput.value);
      return;
    }
    if (selectedChain[1]) {
      await loadChildren(0, selectedChain[0].id, selectedChain[1].id);
    }
    if (selectedChain[2]) {
      await loadChildren(1, selectedChain[1].id, selectedChain[2].id);
      finalInput.value = selectedChain[selectedChain.length - 1].id;
      await loadAttributes(finalInput.value);
      await loadOptions(finalInput.value);
    } else if (selectedChain[1]) {
      finalInput.value = selectedChain[1].id;
      await loadAttributes(finalInput.value);
      await loadOptions(finalInput.value);
    } else {
      finalInput.value = selectedChain[0].id;
      await loadAttributes(finalInput.value);
      await loadOptions(finalInput.value);
    }
    updatePath();
  }

  async function preloadInitialState() {
    if (selectedChain.length) {
      await preloadSelection();
      return;
    }
    const realOptions = Array.from(selects[0].options).filter((option) => option.value);
    if (realOptions.length === 1) {
      selects[0].value = realOptions[0].value;
      await chooseLevel(0);
      return;
    }
    renderEquipmentPicker();
  }

  preloadInitialState().catch(() => {});
})();
