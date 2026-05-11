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
  const equipamentos = window.EQUIPAMENTOS || [];
  const accordions = document.querySelectorAll(".equipment-accordion");
  if (!accordions.length) return;

  const tipoObraSelect = document.getElementById("tipo-obra");
  const editCampos = window.ITEM_EDITANDO_CAMPOS || {};
  const editEquipmentId = window.ITEM_EDITANDO_EQUIPAMENTO_ID;

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

  function makeLabel(text) {
    const label = document.createElement("label");
    label.textContent = text;
    return label;
  }

  function valueFor(equipmentId, campoNome) {
    if (String(editEquipmentId) !== String(equipmentId)) {
      return "";
    }
    return editCampos[campoNome] || "";
  }

  function renderCampo(campo, equipmentId) {
    if (campo.tipo === "info") {
      const info = document.createElement("div");
      info.className = "info-box";
      info.textContent = campo.texto || campo.nome;
      return info;
    }

    const label = makeLabel(campo.nome);
    const name = `campo__${campo.nome}`;
    const value = valueFor(equipmentId, campo.nome);

    if (campo.tipo === "textarea") {
      const input = document.createElement("textarea");
      input.name = name;
      input.rows = 3;
      input.value = value;
      input.required = Boolean(campo.obrigatorio);
      label.appendChild(input);
      return label;
    }

    if (campo.tipo === "select") {
      const input = document.createElement("select");
      input.name = name;
      input.required = Boolean(campo.obrigatorio);
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "Selecione";
      input.appendChild(empty);

      (campo.opcoes || []).forEach((opcao) => {
        const option = document.createElement("option");
        option.value = opcao;
        option.textContent = opcao;
        option.selected = value === opcao;
        input.appendChild(option);
      });

      label.appendChild(input);
      return label;
    }

    if (campo.tipo === "checkbox") {
      const wrap = document.createElement("fieldset");
      const legend = document.createElement("legend");
      legend.textContent = campo.nome;
      wrap.appendChild(legend);
      const selected = Array.isArray(value) ? value : [];

      (campo.opcoes || []).forEach((opcao) => {
        const item = document.createElement("label");
        item.className = "check-row";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.name = name;
        input.value = opcao;
        input.checked = selected.includes(opcao);
        item.appendChild(input);
        item.appendChild(document.createTextNode(opcao));
        wrap.appendChild(item);
      });

      return wrap;
    }

    const input = document.createElement("input");
    input.type = campo.tipo === "number" ? "number" : "text";
    input.name = name;
    input.value = value;
    input.required = Boolean(campo.obrigatorio);
    label.appendChild(input);
    return label;
  }

  function renderFields(accordion) {
    const equipmentId = accordion.dataset.equipmentId;
    const target = accordion.querySelector("[data-fields-for]");
    if (!target || target.dataset.rendered === "true") return;

    const equipamento = equipamentos.find((item) => String(item.id) === String(equipmentId));
    if (!equipamento) return;

    target.innerHTML = "";
    (equipamento.campos || []).forEach((campo) => {
      target.appendChild(renderCampo(campo, equipmentId));
    });
    target.dataset.rendered = "true";
  }

  function setAccordionOpen(accordion, open) {
    const trigger = accordion.querySelector(".accordion-trigger");
    accordion.classList.toggle("open", open);
    trigger.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      renderFields(accordion);
    }
  }

  accordions.forEach((accordion) => {
    const trigger = accordion.querySelector(".accordion-trigger");
    trigger.addEventListener("click", () => {
      const willOpen = !accordion.classList.contains("open");
      accordions.forEach((item) => setAccordionOpen(item, false));
      setAccordionOpen(accordion, willOpen);
    });
  });

  document.querySelectorAll(".situacao-select").forEach(renderSituacao);

  if (tipoObraSelect) {
    tipoObraSelect.addEventListener("change", () => {
      document.querySelectorAll(".situacao-select").forEach((select) => {
        select.dataset.current = "";
        renderSituacao(select);
      });
    });
  }

  const openAccordion = document.querySelector(".equipment-accordion.open");
  if (openAccordion) {
    renderFields(openAccordion);
    openAccordion.scrollIntoView({ block: "center" });
  }
})();
