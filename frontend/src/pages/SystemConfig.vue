<template>
  <div class="system-config-page">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <h3>{{ sidebarCollapsed ? '' : '菜单' }}</h3>
        <el-button
          :icon="sidebarCollapsed ? Expand : Fold"
          text
          @click="sidebarCollapsed = !sidebarCollapsed"
          class="collapse-btn"
        />
      </div>

      <div class="menu-list" v-if="!sidebarCollapsed">
        <div class="menu-item" @click="$router.push('/')">
          <el-icon><HomeFilled /></el-icon>
          <span>图书列表</span>
        </div>
        <div class="menu-item" @click="$router.push('/reading')">
          <el-icon><Reading /></el-icon>
          <span>我的阅读</span>
        </div>
        <div class="menu-item" @click="$router.push('/history')">
          <el-icon><Clock /></el-icon>
          <span>阅读历史</span>
        </div>
        <div class="menu-item" @click="$router.push('/manage')">
          <el-icon><Setting /></el-icon>
          <span>图书管理</span>
        </div>
        <div class="menu-item active">
          <el-icon><Tools /></el-icon>
          <span>系统管理</span>
        </div>
      </div>
    </aside>

    <main class="main-content">
      <header class="page-header">
        <div class="header-left">
          <el-button :icon="Back" circle @click="$router.push('/manage')" />
          <h1>系统管理</h1>
        </div>
      </header>

      <div class="content-area" v-loading="loading">
        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span>AI辅助阅读</span>
            </div>
          </template>
          <el-switch
            v-model="aiEnabled"
            active-text="开启"
            inactive-text="关闭"
            @change="handleAIEnabledChange"
          />
        </el-card>

        <el-card class="config-card" v-loading="modelsLoading">
          <template #header>
            <div class="card-header">
              <span>AI模型配置</span>
              <el-button type="primary" size="small" @click="showAddModelDialog = true">
                添加模型
              </el-button>
            </div>
          </template>

          <el-table :data="models" style="width: 100%">
            <el-table-column prop="name" label="模型名称" width="150" />
            <el-table-column prop="platform" label="平台" width="120" />
            <el-table-column label="API密钥" width="150">
              <template #default="scope">
                <span>{{ scope.row.api_key ? '******' : '未配置' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="默认模型" width="120">
              <template #default="scope">
                <el-tag v-if="defaultModel === scope.row.name" type="success">默认</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="scope">
                <el-button size="small" @click="setDefaultModel(scope.row.name)">
                  设为默认
                </el-button>
                <el-button size="small" type="danger" @click="handleDeleteModel(scope.row.name)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span>AI辅助阅读设置</span>
            </div>
          </template>
          <el-form label-width="150px">
            <el-form-item label="最小内容字数">
              <el-input-number
                v-model="minContentLength"
                :min="0"
                :max="5000"
                :step="100"
              />
              <span style="margin-left: 10px; color: #999;">字数低于此值将跳过生成</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveMinContentLength">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span>AI模型参数</span>
            </div>
          </template>
          <el-alert
            title="参数说明"
            type="info"
            :closable="false"
            style="margin-bottom: 20px;"
          >
            <template #default>
              <div style="font-size: 13px; line-height: 1.8;">
                <p><strong>Temperature:</strong> 控制输出的随机性，值越低输出越确定，推荐0.7</p>
                <p><strong>Max Tokens:</strong> 最大输出token数，值越大生成内容越长</p>
              </div>
            </template>
          </el-alert>

          <el-form :model="selectedModelParams" label-width="150px" v-if="selectedModel">
            <el-form-item label="当前编辑模型">
              <el-select v-model="selectedModel" placeholder="选择模型" @change="loadModelParams">
                <el-option
                  v-for="model in models"
                  :key="model.name"
                  :label="model.name"
                  :value="model.name"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="Temperature">
              <el-slider
                v-model="selectedModelParams.temperature"
                :min="0"
                :max="1"
                :step="0.1"
                show-stops
                style="width: 400px;"
              />
            </el-form-item>
            <el-form-item label="Max Tokens">
              <el-input-number
                v-model="selectedModelParams.max_tokens"
                :min="100"
                :max="4000"
                :step="100"
              />
            </el-form-item>
            <el-form-item label="超时时间(秒)">
              <el-input-number
                v-model="selectedModelParams.timeout"
                :min="60"
                :max="600"
                :step="30"
              />
            </el-form-item>
            <el-form-item label="API协议">
              <el-select v-model="selectedModelApiProtocol" placeholder="选择API协议">
                <el-option label="OpenAI兼容" value="openai-completions" />
                <el-option label="Anthropic兼容" value="anthropic-messages" />
              </el-select>
            </el-form-item>
            <el-form-item label="API密钥">
              <el-input
                v-model="selectedModelApiKey"
                type="password"
                placeholder="请输入API密钥"
                show-password
              />
            </el-form-item>
            <el-form-item label="API地址">
              <el-input
                v-model="selectedModelBaseUrl"
                placeholder="例如: https://api.openai.com/v1"
              />
            </el-form-item>
            <el-form-item label="本地模型路径" v-if="isSelectedModelLocal">
              <el-input
                v-model="selectedModelLocalPath"
                placeholder="例如: llama3"
              />
            </el-form-item>
            <el-form-item label="限速设置">
              <el-input-number
                v-model="selectedModelRateLimit"
                :min="1"
                :max="10"
                :step="1"
              />
              <span style="margin-left: 10px; color: #999;">次/秒</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveModelParams">保存参数</el-button>
            </el-form-item>
          </el-form>
          <el-empty v-else description="请先选择一个模型" />
        </el-card>

        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span>AI提示词模板</span>
              <el-button type="primary" size="small" @click="showAddTemplateDialog = true">
                添加模板
              </el-button>
            </div>
          </template>

          <el-table :data="promptTemplates" style="width: 100%" v-if="promptTemplates.length > 0">
            <el-table-column prop="name" label="模板名称" width="150" />
            <el-table-column prop="description" label="描述" width="200" />
            <el-table-column prop="model_name" label="关联模型" width="150">
              <template #default="scope">
                <span>{{ scope.row.model_name || '使用默认模型' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="scope">
                <el-button size="small" @click="editTemplate(scope.row)">
                  编辑
                </el-button>
                <el-button size="small" type="danger" @click="handleDeleteTemplate(scope.row.name)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无提示词模板" />

          <el-alert
            title="模板说明"
            type="info"
            :closable="false"
            style="margin-top: 20px;"
          >
            <template #default>
              <div style="font-size: 13px; line-height: 1.8;">
                <p>提示词模板中可以使用以下变量：</p>
                <ul style="margin: 10px 0;">
                  <li><strong>{chapter_name}</strong> - 章节名称</li>
                  <li><strong>{content}</strong> - 章节内容</li>
                </ul>
                <p>您可以定义多个模板，每个模板可以配置不同的提示词和关联模型。例如：</p>
                <ul style="margin: 10px 0;">
                  <li>小说摘要模板 - 用于生成小说章节摘要</li>
                  <li>学习内容摘要模板 - 用于生成学习类图书章节内容</li>
                </ul>
                <p>模板选择后会自动保存到本地参数，后续调用时直接使用。</p>
              </div>
            </template>
          </el-alert>
        </el-card>
      </div>
    </main>

    <el-dialog v-model="showAddModelDialog" title="添加AI模型" width="600px">
      <el-form :model="newModel" label-width="120px">
        <el-form-item label="平台" required>
          <el-select v-model="newModel.platform" placeholder="选择平台">
            <el-option label="OpenAI" value="OpenAI" />
            <el-option label="Anthropic" value="Anthropic" />
            <el-option label="MiniMax" value="MiniMax" />
            <el-option label="GLM" value="GLM" />
            <el-option label="Doubao" value="Doubao" />
            <el-option label="Deepseek" value="Deepseek" />
            <el-option label="Google AI" value="Google AI" />
            <el-option label="Ollama" value="Ollama" />
            <el-option label="LM Studio" value="LM Studio" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称" required>
          <el-input v-model="newModel.name" placeholder="例如: gpt-3.5-turbo" />
        </el-form-item>
        <el-form-item label="API协议" required>
          <el-select v-model="newModel.api_protocol" placeholder="选择API协议">
            <el-option label="OpenAI兼容" value="openai-completions" />
            <el-option label="Anthropic兼容" value="anthropic-messages" />
          </el-select>
        </el-form-item>
        <el-form-item label="API密钥" v-if="!isLocalModel">
          <el-input v-model="newModel.api_key" type="password" placeholder="请输入API密钥" />
        </el-form-item>
        <el-form-item label="API地址" required>
          <el-input v-model="newModel.base_url" placeholder="例如: https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="本地模型路径" v-if="isLocalModel">
          <el-input v-model="newModel.local_model_path" placeholder="例如: llama3" />
        </el-form-item>
        <el-form-item label="Temperature">
          <el-slider
            v-model="newModel.parameters.temperature"
            :min="0"
            :max="1"
            :step="0.1"
            show-stops
          />
        </el-form-item>
        <el-form-item label="Max Tokens">
          <el-input-number
            v-model="newModel.parameters.max_tokens"
            :min="100"
            :max="4000"
            :step="100"
          />
        </el-form-item>
        <el-form-item label="超时时间(秒)">
          <el-input-number
            v-model="newModel.parameters.timeout"
            :min="60"
            :max="600"
            :step="30"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddModelDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddModel">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showAddTemplateDialog" :title="editingTemplate ? '编辑提示词模板' : '添加提示词模板'" width="700px">
      <el-form :model="templateForm" label-width="120px">
        <el-form-item label="模板名称" required>
          <el-input v-model="templateForm.name" placeholder="例如: 小说摘要" :disabled="!!editingTemplate" />
        </el-form-item>
        <el-form-item label="模板描述">
          <el-input v-model="templateForm.description" placeholder="例如: 用于生成小说章节摘要" />
        </el-form-item>
        <el-form-item label="关联模型">
          <el-select v-model="templateForm.model_name" placeholder="留空则使用默认模型" clearable>
            <el-option
              v-for="model in models"
              :key="model.name"
              :label="model.name"
              :value="model.name"
            />
          </el-select>
          <span style="margin-left: 10px; color: #999; font-size: 12px;">留空使用默认模型</span>
        </el-form-item>
        <el-form-item label="提示词模板" required>
          <el-input
            v-model="templateForm.prompt_template"
            type="textarea"
            :rows="6"
            placeholder="请输入提示词模板，使用 {chapter_name} 和 {content} 作为占位符"
          />
          <div class="template-hints">
             <span class="hint-label">可用占位符（点击复制）：</span>
             <div class="hint-items">
               <el-tag class="hint-tag" @click="copyToClipboard('{chapter_name}')" style="cursor: pointer;">{chapter_name}</el-tag>
               <span class="hint-desc">- 章节名称</span>
               <el-tag class="hint-tag" @click="copyToClipboard('{content}')" style="cursor: pointer; margin-left: 12px;">{content}</el-tag>
               <span class="hint-desc">- 章节内容</span>
             </div>
           </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeTemplateDialog">取消</el-button>
        <el-button type="primary" @click="handleSaveTemplate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Reading, Setting, HomeFilled, Expand, Fold, Clock, Tools } from '@element-plus/icons-vue'
import api from '@/utils/api.js'

const router = useRouter()
const sidebarCollapsed = ref(false)
const loading = ref(false)
const modelsLoading = ref(false)

const aiEnabled = ref(false)
const models = ref([])
const defaultModel = ref('')
const selectedModel = ref('')
const selectedModelParams = ref({
  temperature: 0.7,
  max_tokens: 1000,
  timeout: 120
})
const selectedModelBaseUrl = ref('')
const selectedModelLocalPath = ref('')
const selectedModelPlatform = ref('')
const selectedModelApiProtocol = ref('openai')
const selectedModelApiKey = ref('')
const selectedModelRateLimit = ref(1)

const isSelectedModelLocal = computed(() => {
  return ['Ollama', 'LM Studio'].includes(selectedModelPlatform.value)
})

const summaryPrompt = ref('')
const minContentLength = ref(300)
const showAddModelDialog = ref(false)
const promptTemplates = ref([])
const showAddTemplateDialog = ref(false)
const editingTemplate = ref(null)
const templateForm = ref({
  name: '',
  description: '',
  model_name: null,
  prompt_template: ''
})
const newModel = ref({
  name: '',
  platform: 'OpenAI',
  api_protocol: 'openai-completions',
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  local_model_path: '',
  parameters: {
    temperature: 0.7,
    max_tokens: 1000,
    timeout: 120
  }
})

const isLocalModel = computed(() => {
  return ['Ollama', 'LM Studio'].includes(newModel.value.platform)
})

watch(() => newModel.value.platform, (newPlatform) => {
  if (newPlatform === 'Ollama') {
    newModel.value.base_url = 'http://localhost:11434/v1'
  } else if (newPlatform === 'LM Studio') {
    newModel.value.base_url = 'http://localhost:1234/v1'
  } else if (newPlatform === 'OpenAI') {
    newModel.value.base_url = 'https://api.openai.com/v1'
  } else if (newPlatform === 'Anthropic') {
    newModel.value.base_url = 'https://api.anthropic.com'
  } else if (newPlatform === 'MiniMax') {
    newModel.value.base_url = 'https://api.minimaxi.com'
  } else if (newPlatform === 'GLM') {
    newModel.value.base_url = 'https://open.bigmodel.cn/api/paas/v4'
  } else if (newPlatform === 'Doubao') {
    newModel.value.base_url = 'https://ark.cn-beijing.volces.com/api/v3'
  } else if (newPlatform === 'Deepseek') {
    newModel.value.base_url = 'https://api.deepseek.com/v1'
  } else if (newPlatform === 'Google AI') {
    newModel.value.base_url = 'https://generativelanguage.googleapis.com/v1beta'
  }
})

const loadConfig = async () => {
  try {
    loading.value = true
    const config = await api.getSystemConfig()
    aiEnabled.value = config.ai_enabled
    models.value = config.models || []
    defaultModel.value = config.default_model || ''
    summaryPrompt.value = config.prompts?.summary || ''
    promptTemplates.value = config.prompt_templates || []

    const minLength = await api.getMinContentLength()
    minContentLength.value = minLength.min_content_length || 300

    if (models.value.length > 0 && !selectedModel.value) {
      selectedModel.value = defaultModel.value || models.value[0].name
      loadModelParams()
    }
  } catch (error) {
    ElMessage.error('加载配置失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadModelParams = () => {
  const model = models.value.find(m => m.name === selectedModel.value)
  if (model) {
    selectedModelPlatform.value = model.platform || ''
    selectedModelApiProtocol.value = model.api_protocol || 'openai-completions'
    selectedModelApiKey.value = model.api_key || ''
    selectedModelBaseUrl.value = model.base_url || ''
    selectedModelLocalPath.value = model.local_model_path || ''
    selectedModelRateLimit.value = model.rate_limit || 1

    if (model.parameters) {
      selectedModelParams.value = {
        temperature: model.parameters.temperature || 0.7,
        max_tokens: model.parameters.max_tokens || 1000,
        timeout: model.parameters.timeout || 120
      }
    }
  }
}

const handleAIEnabledChange = async (value) => {
  try {
    await api.setAIModelEnabled(value)
    ElMessage.success(`AI辅助阅读功能已${value ? '开启' : '关闭'}`)
  } catch (error) {
    ElMessage.error('操作失败')
    aiEnabled.value = !value
    console.error(error)
  }
}

const setDefaultModel = async (modelName) => {
  try {
    await api.setDefaultModel(modelName)
    defaultModel.value = modelName
    ElMessage.success(`已将 ${modelName} 设为默认模型`)
  } catch (error) {
    ElMessage.error('设置默认模型失败')
    console.error(error)
  }
}

const handleDeleteModel = async (modelName) => {
  try {
    await api.deleteAIModel(modelName)
    models.value = models.value.filter(m => m.name !== modelName)
    if (defaultModel.value === modelName) {
      defaultModel.value = models.value.length > 0 ? models.value[0].name : ''
    }
    ElMessage.success(`模型 ${modelName} 已删除`)
  } catch (error) {
    ElMessage.error('删除模型失败')
    console.error(error)
  }
}

const saveModelParams = async () => {
  try {
    const model = models.value.find(m => m.name === selectedModel.value)
    if (model) {
      model.api_protocol = selectedModelApiProtocol.value
      if (selectedModelApiKey.value) {
        model.api_key = selectedModelApiKey.value
      }
      model.base_url = selectedModelBaseUrl.value
      model.local_model_path = selectedModelLocalPath.value
      model.parameters = selectedModelParams.value
      model.rate_limit = selectedModelRateLimit.value
      await api.updateAIModel(model)
      await loadConfig()
      ElMessage.success('模型参数已保存')
    }
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  }
}

const savePrompt = async () => {
  try {
    await api.updatePrompt({
      prompt_type: 'summary',
      prompt_template: summaryPrompt.value
    })
    ElMessage.success('提示词已保存')
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  }
}

const saveMinContentLength = async () => {
  try {
    await api.setMinContentLength(minContentLength.value)
    ElMessage.success('最小内容字数已保存')
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  }
}

const handleAddModel = async () => {
  if (!newModel.value.name || !newModel.value.platform || !newModel.value.base_url) {
    ElMessage.warning('请填写必填项')
    return
  }

  try {
    await api.updateAIModel(newModel.value)
    await loadConfig()
    showAddModelDialog.value = false
    newModel.value = {
      name: '',
      platform: 'openai',
      api_key: '',
      base_url: 'https://api.openai.com/v1',
      local_model_path: '',
      parameters: {
        temperature: 0.7,
        max_tokens: 1000
      }
    }
    ElMessage.success('模型添加成功')
  } catch (error) {
    ElMessage.error('添加模型失败')
    console.error(error)
  }
}

const editTemplate = (template) => {
  editingTemplate.value = template.name
  templateForm.value = {
    name: template.name,
    description: template.description || '',
    model_name: template.model_name || null,
    prompt_template: template.prompt_template || ''
  }
  showAddTemplateDialog.value = true
}

const closeTemplateDialog = () => {
  showAddTemplateDialog.value = false
  editingTemplate.value = null
  templateForm.value = {
    name: '',
    description: '',
    model_name: null,
    prompt_template: ''
  }
}

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success(`已复制: ${text}`)
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

const handleSaveTemplate = async () => {
  if (!templateForm.value.name || !templateForm.value.prompt_template) {
    ElMessage.warning('请填写模板名称和提示词模板')
    return
  }

  try {
    if (editingTemplate.value) {
      await api.updatePromptTemplate(editingTemplate.value, {
        description: templateForm.value.description,
        model_name: templateForm.value.model_name,
        prompt_template: templateForm.value.prompt_template
      })
      ElMessage.success('模板已更新')
    } else {
      await api.addPromptTemplate(templateForm.value)
      ElMessage.success('模板已添加')
    }
    await loadConfig()
    closeTemplateDialog()
  } catch (error) {
    ElMessage.error(editingTemplate.value ? '更新模板失败' : '添加模板失败')
    console.error(error)
  }
}

const handleDeleteTemplate = async (templateName) => {
  try {
    await api.deletePromptTemplate(templateName)
    promptTemplates.value = promptTemplates.value.filter(t => t.name !== templateName)
    ElMessage.success(`模板 ${templateName} 已删除`)
  } catch (error) {
    ElMessage.error('删除模板失败')
    console.error(error)
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.system-config-page {
  display: flex;
  height: 100vh;
  background: #f5f5f5;
}

.sidebar {
  width: 240px;
  background: white;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  transition: width 0.3s;
  display: flex;
  flex-direction: column;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 18px;
}

.collapse-btn {
  font-size: 20px;
}

.menu-list {
  padding: 10px 0;
  flex: 1;
}

.menu-item {
  padding: 15px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.3s;
  color: #666;
}

.menu-item:hover {
  background: #f5f5f5;
  color: #409eff;
}

.menu-item.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: bold;
}

.template-hints {
  margin-top: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
}

.hint-label {
  display: block;
  margin-bottom: 8px;
  color: #909399;
}

.hint-items {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.hint-desc {
  color: #606266;
  margin-left: 4px;
}

.hint-tag {
  margin-right: 4px;
}

.hint-tag:hover {
  opacity: 0.8;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  padding: 20px 30px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}

.content-area {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}

.config-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
