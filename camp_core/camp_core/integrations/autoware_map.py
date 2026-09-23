"""Consume an official projected Lanelet2 map snapshot, not cropped DP vectors.

The C++ bridge exports DP's already loaded map and LaneletRoute lanelet IDs.
The offline example uses Autoware's installed YAML projector and binary helpers.
No Python OSM projection, lane subtype rewriting or traffic phase invention.
"""
import json
from pathlib import Path
import math


class AutowareMap:
    def __init__(self, path):
        self.document = json.loads(Path(path).read_text(encoding='utf-8'))
        if self.document['frame_id'] != 'map':
            raise ValueError('projected Lanelet2 snapshot must be in map frame')
        self.lanelets = {int(row['id']): row for row in self.document['lanelets']}
        self.route_ids = tuple(self.document['route_lanelet_ids'])
        for identifier in self.route_ids:
            if identifier not in self.lanelets:
                raise ValueError('route lanelet is absent from the loaded map')

    def context(self, ego_x, ego_y, ego_yaw, *, signal_authority=None, red_movements=()):
        """Convert full-map geometry to this tick's ego frame.

        Signal authority/movements, when supplied, must be decision-time dynamic
        inputs in the existing CAMP signal schema and local frame. Geometry alone
        leaves signal-dependent atoms typed_missing.
        """
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        from shapely.affinity import affine_transform
        c, s = math.cos(ego_yaw), math.sin(ego_yaw)
        transform = [c, s, -s, c, -c*ego_x-s*ego_y, s*ego_x-c*ego_y]

        def local(points):
            return affine_transform(Polygon([p[:2] for p in points]), transform)

        objects = [dict(id=str(i), kind='lane', geometry=local(self.lanelets[i]['polygon']),
                        lanelet_id=i, attributes=self.lanelets[i]['attributes']) for i in self.route_ids]
        # Original intersection polygons, not fabricated connector IDs.
        for row in self.document['polygons']:
            if row['attributes'].get('type') == 'intersection_area':
                objects.append(dict(id=str(row['id']), kind='intersection_area', geometry=local(row['points'])))
        road = [local(row['polygon']) for row in self.lanelets.values()
                if row['attributes'].get('subtype') in ('road', 'highway')]
        signal = signal_authority if signal_authority is not None else dict(
            source_state='typed_missing', reason='no_decision_time_signal_phase_input')
        return dict(route_atom_context=dict(route_objects=tuple(objects),
                    red_movements=tuple(red_movements), signal_source_state=signal['source_state'],
                    source_authority='official_projected_lanelet_map_and_route'),
                    signal_authority=signal,
                    drivable_area_geometry=unary_union(road) if road else None,
                    drivable_area_source_authority='full_loaded_map_road_highway_lanelet_union')
