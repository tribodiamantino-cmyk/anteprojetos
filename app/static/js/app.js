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
    if ((isFluxoSelected() || isTransportadorSelected()) && finalFields.some((element) => element.hidden)) {
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
