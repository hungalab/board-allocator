#include <Python.h>

#include <set>
#include <vector>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>

class Flow {
public:
    int cvid;
    std::set<std::pair<int, int>> edges;

    Flow(int c, std::set<std::pair<int, int>>& e): cvid(c), edges(e) { }
};

class Vdeg {
public:
    int index;
    int deg;

    Vdeg(int i, int d): index(i), deg(d) { }

    bool operator<(const Vdeg& v) {
        return this->deg < v.deg;
    }
};

static PyObject* cpp_crossing_flows(PyObject*, PyObject* args) {
    PyObject* flow_tuples = NULL;
    if (!PyArg_ParseTuple(args, "O", &flow_tuples)) {
        return NULL;
    }

    // make flows
    std::vector<Flow> flows;
    if (flow_tuples == NULL) {
        PyErr_SetString(PyExc_TypeError, "no flows");
        return NULL;
    }
    PyObject* i = PyObject_GetIter(flow_tuples);
    if (i == NULL) {
        return NULL;
    }
    PyObject* ftuple;
    while ((ftuple = PyIter_Next(i))) {
        PyObject* j = PyObject_GetIter(ftuple);
        if (j == NULL) {
            return NULL;
        }

        int flow_id;
        PyObject* fid = PyIter_Next(j);
        if (!PyLong_Check(fid)) {
            PyErr_SetString(PyExc_TypeError, "invalid flow_id");
            return NULL;
        }
        flow_id = PyLong_AsLong(fid);

        std::set<std::pair<int, int>> edges;
        PyObject* pyedges = PyIter_Next(j);
        PyObject* k = PyObject_GetIter(pyedges);
        if (k == NULL) {
            return NULL;
        }
        PyObject* eo;
        while ((eo = PyIter_Next(k))) {
            PyObject* l = PyObject_GetIter(eo);
            if (l == NULL) {
                return NULL;
            }
            std::vector<int> e;
            PyObject* vo;
            while ((vo = PyIter_Next(l))) {
                if (!PyLong_Check(vo)) {
                    PyErr_SetString(PyExc_TypeError, "invalid graph");
                    return NULL;
                }
                e.push_back(PyLong_AsLong(vo));
            }
            assert(e.size() == 2);
            edges.insert(std::make_pair(e[0], e[1]));
        }
        
        Flow flow(flow_id, edges);
        flows.push_back(flow);
    }

    // create edge set
    PyObject* crossings = PySet_New(NULL);
    std::vector<Flow>::iterator i_iter, j_iter;
    for (i_iter = flows.begin(); i_iter != flows.end(); ++i_iter) {
        for (j_iter = std::next(i_iter); j_iter != flows.end(); ++j_iter) {
            std::set<std::pair<int, int>> intersection_set, i_set, j_set;
            i_set = i_iter->edges;
            j_set = j_iter->edges;
            std::set_intersection(i_set.begin(), i_set.end(), 
                                  j_set.begin(), j_set.end(), 
                                  std::inserter(intersection_set, intersection_set.end()));
            if (intersection_set.size()) {
                PySet_Add(crossings, Py_BuildValue("(ii)", i_iter->cvid, j_iter->cvid));
            }
        }
    }

    return crossings;
}

static PyObject* cpp_crossings_for_a_flow(PyObject*, PyObject* args) {
    PyObject* target_flow_tuple = NULL;
    PyObject* flow_tuples = NULL;
    if (!PyArg_ParseTuple(args, "OO", &target_flow_tuple, &flow_tuples)) {
        return NULL;
    }

    // make target_flow
    Flow* target_flow;
    if (target_flow_tuple == NULL) {
        PyErr_SetString(PyExc_TypeError, "no flows");
        return NULL;
    }
    PyObject* i = PyObject_GetIter(target_flow_tuple);
    if (i == NULL) {
        return NULL;
    }

    int flow_id;
    PyObject* fid = PyIter_Next(i);
    if (!PyLong_Check(fid)) {
        PyErr_SetString(PyExc_TypeError, "invalid flow_id");
        return NULL;
    }
    flow_id = PyLong_AsLong(fid);

    std::set<std::pair<int, int>> edges;
    PyObject* pyedges = PyIter_Next(i);
    PyObject* j = PyObject_GetIter(pyedges);
    if (j == NULL) {
        return NULL;
    }
    PyObject* eo;
    while ((eo = PyIter_Next(j))) {
        PyObject* k = PyObject_GetIter(eo);
        if (k == NULL) {
            return NULL;
        }
        std::vector<int> e;
        PyObject* vo;
        while ((vo = PyIter_Next(k))) {
            if (!PyLong_Check(vo)) {
                PyErr_SetString(PyExc_TypeError, "invalid graph");
                return NULL;
            }
            e.push_back(PyLong_AsLong(vo));
        }
        assert(e.size() == 2);
        edges.insert(std::make_pair(e[0], e[1]));
    }
    target_flow = new Flow(flow_id, edges);

    // make flows
    std::vector<Flow> flows;
    if (flow_tuples == NULL) {
        PyErr_SetString(PyExc_TypeError, "no flows");
        return NULL;
    }
    i = PyObject_GetIter(flow_tuples);
    if (i == NULL) {
        return NULL;
    }
    PyObject* ftuple;
    while ((ftuple = PyIter_Next(i))) {
        PyObject* j = PyObject_GetIter(ftuple);
        if (j == NULL) {
            return NULL;
        }

        int flow_id;
        PyObject* fid = PyIter_Next(j);
        if (!PyLong_Check(fid)) {
            PyErr_SetString(PyExc_TypeError, "invalid flow_id");
            return NULL;
        }
        flow_id = PyLong_AsLong(fid);

        std::set<std::pair<int, int>> edges;
        PyObject* pyedges = PyIter_Next(j);
        PyObject* k = PyObject_GetIter(pyedges);
        if (k == NULL) {
            return NULL;
        }
        PyObject* eo;
        while ((eo = PyIter_Next(k))) {
            PyObject* l = PyObject_GetIter(eo);
            if (l == NULL) {
                return NULL;
            }
            std::vector<int> e;
            PyObject* vo;
            while ((vo = PyIter_Next(l))) {
                if (!PyLong_Check(vo)) {
                    PyErr_SetString(PyExc_TypeError, "invalid graph");
                    return NULL;
                }
                e.push_back(PyLong_AsLong(vo));
            }
            assert(e.size() == 2);
            edges.insert(std::make_pair(e[0], e[1]));
        }
        
        Flow flow(flow_id, edges);
        flows.push_back(flow);
    }

    // create crossing flow_id set
    std::unordered_set<int> crossings;
    std::vector<Flow>::iterator iter;
    for (iter = flows.begin(); iter != flows.end(); ++iter) {
        if (target_flow->cvid != iter->cvid) {
            std::set<std::pair<int, int>> intersection_set;
            std::set_intersection((target_flow->edges).begin(), (target_flow->edges).end(), 
                                  (iter->edges).begin(), (iter->edges).end(), 
                                  std::inserter(intersection_set, intersection_set.end()));
            if (intersection_set.size()) {
                crossings.insert(iter->cvid);
            }
        }
    }

    return Py_BuildValue("i", crossings.size());
}

static PyObject* cpp_slot_allocation(PyObject*, PyObject* args) {
    PyObject* flow_tuples = NULL;
    if (!PyArg_ParseTuple(args, "O", &flow_tuples)) {
        return NULL;
    }

    // make flows
    std::vector<Flow> flows;
    if (flow_tuples == NULL) {
        PyErr_SetString(PyExc_TypeError, "no flows");
        return NULL;
    }
    PyObject* i = PyObject_GetIter(flow_tuples);
    if (i == NULL) {
        return NULL;
    }
    PyObject* ftuple;
    while ((ftuple = PyIter_Next(i))) {
        PyObject* j = PyObject_GetIter(ftuple);
        if (j == NULL) {
            return NULL;
        }

        int flow_id;
        PyObject* fid = PyIter_Next(j);
        if (!PyLong_Check(fid)) {
            PyErr_SetString(PyExc_TypeError, "invalid flow_id");
            return NULL;
        }
        flow_id = PyLong_AsLong(fid);

        std::set<std::pair<int, int>> edges;
        PyObject* pyedges = PyIter_Next(j);
        PyObject* k = PyObject_GetIter(pyedges);
        if (k == NULL) {
            return NULL;
        }
        PyObject* eo;
        while ((eo = PyIter_Next(k))) {
            PyObject* l = PyObject_GetIter(eo);
            if (l == NULL) {
                return NULL;
            }
            std::vector<int> e;
            PyObject* vo;
            while ((vo = PyIter_Next(l))) {
                if (!PyLong_Check(vo)) {
                    PyErr_SetString(PyExc_TypeError, "invalid graph");
                    return NULL;
                }
                e.push_back(PyLong_AsLong(vo));
            }
            assert(e.size() == 2);
            edges.insert(std::make_pair(e[0], e[1]));
        }
        
        Flow flow(flow_id, edges);
        flows.push_back(flow);
    }

    // create graph
    std::unordered_map<int, std::unordered_set<int>> graph;
    std::vector<Flow>::iterator i_iter, j_iter;
    for (i_iter = flows.begin(); i_iter != flows.end(); ++i_iter) {
        for (j_iter = std::next(i_iter); j_iter != flows.end(); ++j_iter) {
            // make adj set if null
            if (graph.find(i_iter->cvid) == graph.end()) {
                std::unordered_set<int> empty_set{};
                graph.emplace(i_iter->cvid, empty_set);
            }
            if (graph.find(j_iter->cvid) == graph.end()) {
                std::unordered_set<int> empty_set{};
                graph.emplace(j_iter->cvid, empty_set);
            }

            // if crossing, set value to adj list
            std::set<std::pair<int, int>> intersection_set, i_set, j_set;
            i_set = i_iter->edges;
            j_set = j_iter->edges;
            std::set_intersection(i_set.begin(), i_set.end(), 
                                  j_set.begin(), j_set.end(), 
                                  std::inserter(intersection_set, intersection_set.end()));
            if (intersection_set.size()) {
                // for i_iter
                graph[i_iter->cvid].insert(j_iter->cvid);
                // for j_iter
                graph[j_iter->cvid].insert(i_iter->cvid);
            }
        }
    }

    // make vertex index list sorted by degree
    std::vector<Vdeg> vdeg_list;
    std::unordered_map<int, std::unordered_set<int>>::iterator iter;
    for (iter = graph.begin(); iter != graph.end(); ++iter) {
        Vdeg v(iter->first, (iter->second).size());
        vdeg_list.push_back(v);
    }
    std::sort(vdeg_list.rbegin(), vdeg_list.rend());

    // Welsh-Powell graph coloring algorithm
    std::unordered_map<int, int> coloring;
    std::vector<Vdeg>::iterator vdeg_iter;
    for (vdeg_iter = vdeg_list.begin(); vdeg_iter != vdeg_list.end(); ++vdeg_iter) {
        std::unordered_set<int> neighbour_colors;
        std::unordered_set<int> adj = graph[vdeg_iter->index];
        std::unordered_set<int>::iterator viter;
        for (viter = adj.begin(); viter != adj.end(); ++viter) {
            if (coloring.find(*viter) != coloring.end()) {
                neighbour_colors.insert(coloring[*viter]);
            }
        }
        int color_id;
        for (color_id = 0; ; ++color_id) {
            if (neighbour_colors.find(color_id) == neighbour_colors.end()) {
                break;
            }
        }
        coloring.emplace(vdeg_iter->index, color_id);
    }

    // convert to PyObject
    PyObject* pycoloring = PyDict_New();
    std::unordered_map<int, int>::iterator citer;
    for (citer = coloring.begin(); citer != coloring.end(); ++citer) {
        PyDict_SetItem(pycoloring, Py_BuildValue("i", citer->first), Py_BuildValue("i", citer->second));
    }

    return pycoloring;
}

static PyMethodDef mod_methods[] = {
    {"crossing_flows", cpp_crossing_flows, METH_VARARGS},
    {"crossings_for_a_flow", cpp_crossings_for_a_flow, METH_VARARGS},
    {"slot_allocation", cpp_slot_allocation, METH_VARARGS},
    {NULL},
};

static struct PyModuleDef mod_def = {
    PyModuleDef_HEAD_INIT,
    "cpp_modules",
    "crossing_flows written in C",
    -1,
    mod_methods
};

//module creator
PyMODINIT_FUNC PyInit_cpp_modules(void)
{
    return PyModule_Create(&mod_def);
}