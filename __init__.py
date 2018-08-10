bl_info = {
	"name": "Vray Material textures",
	"author": "JuhaW",
	"version": (1, 0, 0, 0),
	"blender": (2, 7, 9, 0),
	"api": 44539,
	"category": "Material",
	"location": "Properties > Material",
	"description": "Show uw mapped image textures on viewport",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "", }

import bpy
from bpy.props import StringProperty, IntProperty

class Vray_Mat_Show_Texture(bpy.types.Operator):
	'''Show selected objects uv mapped image textures on viewport'''
	bl_idname = "vray.show_textures"
	bl_label = "Show material textures"
		
		
	def execute(self, context):

		bpy.context.scene.tool_settings.use_uv_select_sync = True
		area_changed = False
		area = [area for area in bpy.context.screen.areas if area.type == 'IMAGE_EDITOR']
		if not area:
			#print ("not image editor found")
			area = [i for i in bpy.context.screen.areas if i.type == "PROPERTIES"][0]
			area.type = 'IMAGE_EDITOR'
			area_changed = True
		else:
			area = area[0]
			
		bpy.context.scene.render.engine = 'BLENDER_RENDER'
		
		sel_objs = [i for i in bpy.context.selected_objects if i.type == 'MESH']
		for o in sel_objs:
			
			#print ("mesh object:", o.name)
			bpy.context.scene.objects.active = o
			mode = o.mode
			#print ("create textures")
			create_textures(o, area, True)
			
			bpy.ops.object.mode_set(mode = mode)
		
		if area_changed:
			area.type = 'PROPERTIES'
		
		#bpy.ops.object.mode_set(mode = 'EDIT')
		bpy.context.scene.render.engine = 'VRAY_RENDER_RT'
		
		
		return {'FINISHED'}	

def Vray_material_panel(self, context):
	
	layout = self.layout
	layout.operator('vray.show_textures', icon = 'IMAGE_DATA')


###############################################################

def outputnode_search(mat): #return node/None
	
	for node in mat.vray.ntree.nodes:
		#print (mat.name, node)
		if node.bl_idname == 'VRayNodeOutputMaterial' and node.inputs[0].is_linked:
			return node

	print ("No material output node found")
	return None
			
###############################################################
def nodes_iterate(mat, node_type_search = False): #return image/nodeindex/None
	#node_type_search = True when searching nodetype for proxy save

	nodeoutput = outputnode_search(mat)
	if nodeoutput is None:
		return None
	#print ("Material: ",mat)

	nodelist = []
	nodelist.append(nodeoutput)
	nodecounter = 0

	while nodecounter < len(nodelist):

		basenode = nodelist[nodecounter]

		#print ("basenode",basenode, mat)
		#search nodetype
		if node_type_search:
			if node_type_check(basenode.vray_plugin):
				return mat.vray.ntree.nodes.find(basenode.name)
		#search image texture
		elif hasattr(basenode, 'vray_plugin') and basenode.vray_plugin in ('TexBitmap','BitmapBuffer'):
			#print ("Mat:",mat.name, "has bitmap texture")
			#print ("basenode.name"	, basenode.name)

			if hasattr(basenode, 'texture'):
				if hasattr(basenode.texture, 'image'):
					image = basenode.texture.image
					#print ("image=", image)
					return image

		inputlist = (i for i in basenode.inputs if i.is_linked)

		for input in inputlist:

			for nlinks in input.links:

				node = nlinks.from_node
				if node not in nodelist:
					nodelist.append(node)

		nodecounter +=1

	return None

###############################################################

def create_textures(o, area, shadeless):
	#print ("##################################")

	bpy.ops.object.mode_set(mode = 'EDIT')
	#o = bpy.context.object
	o.update_from_editmode()
	sel_faces = [i.index for i in o.data.polygons if i.select]
	bpy.ops.mesh.select_all(action='DESELECT')
	
	cur_mat_ind = o.active_material_index
	matind = 0
	cur_mat_image = None
	
		
					
	for slot in o.material_slots:
		#filter out materials without nodetree
		#materials = [m for m in bpy.data.materials if hasattr(m.vray.ntree, "name")]
		#for mat in materials:
		o.active_material_index = matind
		
		mat = slot.material
		bpy.ops.object.material_slot_select()
		#o.update_from_editmode()
		#print ("material slot selected:", matind)
		#if material slot is empty, skip it
		#if not vray material, skip it
		if not mat or not mat.vray.ntree:
			print ("No Vray material: ", matind)
			continue
		image = nodes_iterate(mat)
		
		#3d viewport 
		mat.use_shadeless = shadeless
		mat.use_nodes = False
		mat.use_transparency = True
		mat.alpha = 0
		

		#create image texture
		#print ("image:",image)
		#check if image file node is selected, it overrites image which is shown at 3dview
				
		if image:
			#print ("image is not none")
			#print (mat.name)
			#create image texture if needed
			if matind == cur_mat_ind:
				cur_mat_image = image
				#print ("set current material image", image)
			if mat.name in bpy.data.textures:
				tex = bpy.data.textures[mat.name]
			else:
				tex = bpy.data.textures.new(mat.name,'IMAGE')

			tex.image = image
			tex.type = 'IMAGE'
			
			mat.texture_slots.clear(0)
			mat.texture_slots.add()
			mat.texture_slots[0].texture = tex
			mat.texture_slots[0].use_map_alpha = True
			
			# how many materials
			#len([i for i in o.data.materials if i is not None])
			#print ("area:", area.type)
			node = mat.vray.ntree.nodes.active
			if hasattr(node, 'vray_plugin') and node and node.vray_plugin == 'TexBitmap':
				area.spaces[0].image = node.texture.image
				#print ("texture in image editor:", node.texture.image.name)
			else:
				area.spaces[0].image = image
				#print ("texture in image editor:", image.name)
		
		#bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)	
		bpy.ops.wm.redraw_timer(type='DRAW_SWAP', iterations=1)	
		matind += 1
		bpy.ops.mesh.select_all(action='DESELECT')
		
	if cur_mat_image:
			area.spaces[0].image = cur_mat_image			
	o.active_material_index = cur_mat_ind
	
	bpy.ops.object.mode_set(mode = 'OBJECT')
	for i in sel_faces:
		o.data.polygons[i].select = True
	

###############################################################		
#nodes types with image


def node_type_check(nodetype):
	
	MaterialTypeFilter = {
	'MtlSingleBRDF', 'MtlVRmat', 'MtlDoubleSided', 'MtlGLSL', 'MtlLayeredBRDF', 'MtlDiffuse',
	'MtlBump', 'Mtl2Sided', 'MtlMulti',
	'MtlWrapper',
	'MtlWrapperMaya', 'MayaMtlMatte', 'MtlMaterialID', 'MtlMayaRamp', 'MtlObjBBox',
	'MtlOverride', 'MtlRenderStats', 'MtlRoundEdges', 'MtlStreakFade'}
	
	return nodetype in MaterialTypeFilter



# REGISTRATION ------------------------------------------------------
def register():

	bpy.utils.register_module(__name__)
	bpy.types.VRAY_MP_context_material.append(Vray_material_panel)

def unregister():

	bpy.types.VRAY_MP_context_material.append(Vray_material_panel)
	bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
	register()
