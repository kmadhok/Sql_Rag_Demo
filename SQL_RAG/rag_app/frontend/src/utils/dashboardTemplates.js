/**
 * Dashboard Templates
 *
 * Pre-configured dashboard layouts for quick setup.
 * Templates define grid layouts but don't include actual queries.
 * Users will need to add their own saved queries after creation.
 */

export const DASHBOARD_TEMPLATES = [
  {
    id: 'blank',
    name: 'Blank Dashboard',
    description: 'Start from scratch with an empty dashboard',
    icon: '📄',
    layoutItems: [],
  },
  {
    id: 'single-focus',
    name: 'Single Focus',
    description: 'One large chart for detailed analysis',
    icon: '🎯',
    layoutItems: [
      {
        i: 'template-1',
        x: 0,
        y: 0,
        w: 12,
        h: 4,
        minW: 6,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'column',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
    ],
  },
  {
    id: 'two-column',
    name: 'Two Column',
    description: 'Two equal-width charts side by side',
    icon: '⚖️',
    layoutItems: [
      {
        i: 'template-1',
        x: 0,
        y: 0,
        w: 6,
        h: 3,
        minW: 3,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'column',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
      {
        i: 'template-2',
        x: 6,
        y: 0,
        w: 6,
        h: 3,
        minW: 3,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'line',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
    ],
  },
  {
    id: 'kpi-grid',
    name: 'KPI Grid',
    description: 'Four charts in a grid layout for metrics overview',
    icon: '📊',
    layoutItems: [
      {
        i: 'template-1',
        x: 0,
        y: 0,
        w: 6,
        h: 2,
        minW: 3,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'column',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
      {
        i: 'template-2',
        x: 6,
        y: 0,
        w: 6,
        h: 2,
        minW: 3,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'pie',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
      {
        i: 'template-3',
        x: 0,
        y: 2,
        w: 6,
        h: 2,
        minW: 3,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'line',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
      {
        i: 'template-4',
        x: 6,
        y: 2,
        w: 6,
        h: 2,
        minW: 3,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'bar',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
    ],
  },
  {
    id: 'executive-summary',
    name: 'Executive Summary',
    description: 'One wide chart on top, two smaller charts below',
    icon: '📈',
    layoutItems: [
      {
        i: 'template-1',
        x: 0,
        y: 0,
        w: 12,
        h: 3,
        minW: 6,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'area',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
      {
        i: 'template-2',
        x: 0,
        y: 3,
        w: 6,
        h: 2,
        minW: 3,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'column',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
      {
        i: 'template-3',
        x: 6,
        y: 3,
        w: 6,
        h: 2,
        minW: 3,
        minH: 2,
        saved_query_id: '',
        query_question: '',
        chart_config: {
          chartType: 'pie',
          xColumn: null,
          yColumn: null,
          aggregation: 'count',
        },
      },
    ],
  },
];

/**
 * Get template by ID
 */
export function getTemplateById(templateId) {
  return DASHBOARD_TEMPLATES.find((t) => t.id === templateId);
}

/**
 * Apply template to create layout items with unique IDs
 */
export function applyTemplate(templateId) {
  const template = getTemplateById(templateId);
  if (!template) return [];

  // Generate new unique IDs for each item
  return template.layoutItems.map((item, index) => ({
    ...item,
    i: `chart-${Date.now()}-${index}`,
  }));
}
